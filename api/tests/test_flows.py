import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import make_conninfo

from wallnut.db import connect, migrate
from wallnut.demo import ACTIVITIES, PASSWORD, seed
from wallnut.main import app

ACTIVE = str(ACTIVITIES[0][0])
FUTURE = str(ACTIVITIES[1][0])


@pytest.fixture
def scenario(monkeypatch):
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        pytest.fail("Define TEST_DATABASE_URL con una base PostgreSQL de pruebas.")
    schema = f"test_{uuid4().hex}"
    monkeypatch.setenv("DATABASE_URL", test_url)
    with connect() as administrator:
        administrator.execute(f"CREATE SCHEMA {schema}")
        monkeypatch.setenv("DATABASE_URL", make_conninfo(test_url, options=f"-c search_path={schema}"))
        try:
            with connect() as db:
                migrate(db)
                migrate(db)
                seed(db)
            with TestClient(app) as client:
                yield client
        finally:
            administrator.execute(f"DROP SCHEMA {schema} CASCADE")


def session(client, handle):
    response = client.post("/v1/session", json={
        "email": f"{handle}@example.test", "password": PASSWORD,
    })
    assert response.status_code == 200
    assert "password_hash" not in response.json()["member"]
    return {"Authorization": f"Bearer {response.json()['token']}"}


def issue(client, organizer, activity_id=ACTIVE):
    response = client.post(f"/v1/activities/{activity_id}/code", headers=organizer)
    assert response.status_code == 200
    return response.json()["code"]


def attend(client, student, code, activity_id=ACTIVE):
    return client.post(f"/v1/activities/{activity_id}/attendance", headers=student, json={"code": code})


def send(client, sender, points, request_id=None, recipient="nico"):
    return client.post("/v1/transfers", headers=sender, json={
        "recipient": recipient, "points": points,
        "request_id": request_id or str(uuid4()),
    })


def wallet(client, member):
    response = client.get("/v1/wallet", headers=member)
    assert response.status_code == 200
    return response.json()


def test_authenticated_session_and_logout(scenario):
    assert scenario.get("/v1/wallet").status_code == 401
    assert scenario.post("/v1/session", json={
        "email": "vale@example.test", "password": "equivocada",
    }).status_code == 401
    vale = session(scenario, "vale")
    assert wallet(scenario, vale) == {"balance": 0, "movements": []}
    assert scenario.delete("/v1/session", headers=vale).status_code == 204
    assert scenario.get("/v1/wallet", headers=vale).status_code == 401


def test_publish_and_rotate_codes(scenario):
    vale = session(scenario, "vale")
    organizer = session(scenario, "organiza")
    now = datetime.now(timezone.utc)
    body = {
        "title": "Actividad nueva", "location": "Salón 1", "description": "Piloto",
        "starts_at": (now - timedelta(minutes=10)).isoformat(),
        "ends_at": (now + timedelta(minutes=15)).isoformat(), "reward": 10,
    }
    assert scenario.post("/v1/activities", headers=vale, json=body).status_code == 403
    assert scenario.post(f"/v1/activities/{ACTIVE}/code", headers=vale).status_code == 403
    response = scenario.post("/v1/activities", headers=organizer, json=body)
    assert response.status_code == 201
    activity_id = response.json()["id"]
    assert scenario.post(f"/v1/activities/{FUTURE}/code", headers=organizer).status_code == 409
    old_code = issue(scenario, organizer, activity_id)
    new_code = issue(scenario, organizer, activity_id)
    assert attend(scenario, vale, old_code, activity_id).status_code == 409
    assert attend(scenario, vale, new_code, ACTIVE).status_code == 409
    catalog = scenario.get("/v1/activities", headers=vale).json()
    item = next(item for item in catalog if item["id"] == activity_id)
    assert not item["can_issue_code"]
    assert {"code", "checkin_hash", "checkin_expires_at"}.isdisjoint(item)
    with connect() as db:
        db.execute(
            "UPDATE activities SET checkin_expires_at = now() - interval '1 second' WHERE id = %s",
            (activity_id,),
        )
    assert attend(scenario, vale, new_code, activity_id).status_code == 409


def test_participation_transfer_and_ranking(scenario):
    vale = session(scenario, "vale")
    nico = session(scenario, "nico")
    organizer = session(scenario, "organiza")
    code = issue(scenario, organizer)
    recorded = attend(scenario, vale, code).json()
    assert recorded["points"] == 30 and not recorded["already_recorded"]
    retry = attend(scenario, vale, code).json()
    assert retry["id"] == recorded["id"] and retry["already_recorded"]
    request_id = str(uuid4())
    response = send(scenario, vale, 12, request_id)
    assert response.status_code == 200
    assert send(scenario, vale, 12, request_id).json() == response.json()
    assert send(scenario, vale, 13, request_id).status_code == 409
    assert wallet(scenario, vale)["balance"] == 18
    assert [item["points"] for item in wallet(scenario, vale)["movements"]] == [-12, 30]
    assert wallet(scenario, nico)["balance"] == 12
    assert scenario.get("/v1/ranking", headers=nico).json() == [
        {"position": 1, "handle": "vale", "display_name": "Valentina", "points": 30}
    ]
    answer = scenario.post("/v1/ardi/messages", headers=nico, json={"message": "¿Qué actividades hay?"})
    assert "Exploración del campus" in answer.json()["answer"]


def test_concurrent_claims_award_once(scenario):
    vale = session(scenario, "vale")
    code = issue(scenario, session(scenario, "organiza"))
    with ThreadPoolExecutor(max_workers=2) as executor:
        claims = list(executor.map(lambda _: attend(scenario, vale, code), range(2)))
    assert [response.status_code for response in claims] == [200, 200]
    assert sorted(response.json()["already_recorded"] for response in claims) == [False, True]
    assert wallet(scenario, vale)["balance"] == 30


def test_concurrent_transfers_cannot_overdraw(scenario):
    vale = session(scenario, "vale")
    nico = session(scenario, "nico")
    code = issue(scenario, session(scenario, "organiza"))
    assert attend(scenario, vale, code).status_code == 200
    assert send(scenario, vale, 0).status_code == 422
    assert send(scenario, vale, 1, recipient="vale").status_code == 422
    assert send(scenario, vale, 1, recipient="fantasma").status_code == 404
    with ThreadPoolExecutor(max_workers=2) as executor:
        transfers = list(executor.map(lambda _: send(scenario, vale, 20), range(2)))
    assert sorted(response.status_code for response in transfers) == [200, 409]
    assert wallet(scenario, vale)["balance"] == 10
    assert wallet(scenario, nico)["balance"] == 20

