import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import make_conninfo

from wallnut.database import connect, migrate
from wallnut.demo import simulated_identity
from wallnut.main import create_app


def fake_verifier(credential):
    if credential == "personal":
        return {"sub": "personal", "email": "pers@example.test",
                "email_verified": True, "hd": "example.test"}
    if credential == "unverified":
        return {**simulated_identity("demo-student"), "email_verified": False}
    if credential == "external-staff":
        return {"sub": "other-faculty", "email": "otra.profesor@unibague.edu.co",
                "email_verified": True, "hd": "unibague.edu.co", "name": "Otra docente"}
    return simulated_identity(credential)


@pytest.fixture
def client(monkeypatch):
    address = os.environ.get("TEST_DATABASE_URL")
    if not address:
        pytest.fail("Configura TEST_DATABASE_URL con una base PostgreSQL de pruebas.")
    schema = f"test_{uuid4().hex}"
    monkeypatch.setenv("DATABASE_URL", address)
    with connect() as admin:
        admin.execute(f"CREATE SCHEMA {schema}")
        monkeypatch.setenv("DATABASE_URL", make_conninfo(address, options=f"-c search_path={schema}"))
        try:
            with connect() as db:
                migrate(db)
                migrate(db)
            yield TestClient(create_app(fake_verifier))
        finally:
            admin.execute(f"DROP SCHEMA {schema} CASCADE")


def sign_in(client, credential):
    result = client.post("/v1/session", json={"credential": credential})
    assert result.status_code == 200, result.text
    session = result.json()
    assert result.headers["cache-control"] == "no-store"
    return {"Authorization": f"Bearer {session['token']}"}, session["account"]


def setup_campus(client):
    admin, admin_account = sign_in(client, "demo-admin")
    with connect() as db:
        db.execute("UPDATE accounts SET role = 'admin' WHERE id = %s", (admin_account["id"],))
    faculty, teacher = sign_in(client, "demo-faculty")
    assert client.post("/v1/faculty", headers=admin, json={"email": teacher["email"]}).status_code == 200
    assert client.get("/v1/faculty", headers=admin).json()[0]["id"] == teacher["id"]
    result = client.post("/v1/courses", headers=admin, json={
        "code": "MAT303", "title": "Cálculo III", "term": "PILOTO",
        "section": "01", "faculty_id": teacher["id"],
    })
    assert result.status_code == 201, result.text
    return admin, faculty, result.json()["id"]


def create_call(client, faculty, course):
    result = client.post("/v1/workshop-calls", headers=faculty, json={
        "course_id": course, "title": "Se busca tallerista",
        "description": "Guía un taller de series y convergencia.",
    })
    assert result.status_code == 201, result.text
    return result.json()["id"]


def apply(client, student, call):
    return client.post(f"/v1/workshop-calls/{call}/applications", headers=student, json={
        "proposal": "Explicaré los criterios con ejercicios.", "evidence_url": "https://example.test/docs",
    })


def approval(client, faculty, call, application):
    return client.put(f"/v1/workshop-calls/{call}/applications/{application}/approval", headers=faculty)


def test_verified_signup_and_logout(client):
    assert client.get("/v1/workshop-calls").status_code == 401
    for credential in ("personal", "unverified"):
        assert client.post("/v1/session", json={"credential": credential}).status_code == 403
    student, account = sign_in(client, "demo-student")
    assert account["role"] == "student"
    _, returning = sign_in(client, "demo-student")
    assert returning["id"] == account["id"]
    assert client.delete("/v1/session", headers=student).status_code == 204
    assert client.get("/v1/session", headers=student).status_code == 401


def test_campus_and_confirmed_student_enrollment(client):
    admin, faculty, course = setup_campus(client)
    student, maria = sign_in(client, "demo-student")
    assert client.get("/v1/courses", headers=student).json() == []
    endpoint = f"/v1/courses/{course}/students"
    body = {"email": maria["email"]}
    assert client.put(endpoint, headers=student, json=body).status_code == 403
    enrolled = client.put(endpoint, headers=faculty, json=body)
    assert enrolled.status_code == 200
    assert client.put(endpoint, headers=admin, json=body).json() == enrolled.json()
    assert client.get("/v1/courses", headers=student).json()[0]["enrolled"]
    assert client.post("/v1/faculty", headers=student, json=body).status_code == 403


def test_call_publication_and_facilitator_approval(client):
    _, faculty, course = setup_campus(client)
    student, _ = sign_in(client, "demo-student")
    unauthorized, _ = sign_in(client, "external-staff")
    assert client.post("/v1/workshop-calls", headers=student, json={
        "course_id": course, "title": "Convocatoria",
        "description": "Descripción de una convocatoria.",
    }).status_code == 403

    call = create_call(client, faculty, course)
    result = apply(client, student, call)
    assert result.status_code == 201
    application = result.json()["id"]
    assert apply(client, student, call).status_code == 409
    assert approval(client, unauthorized, call, application).status_code == 403
    assert client.get(f"/v1/workshop-calls/{call}/applications", headers=student).status_code == 403
    approved = approval(client, faculty, call, application)
    assert approved.json()["status"] == "approved"
    assert approval(client, faculty, call, application).json() == approved.json()
    feed_item = client.get("/v1/workshop-calls", headers=student).json()[0]
    assert not feed_item["open"] and feed_item["my_application"] == "approved"
    assert "proposal" not in feed_item and "evidence_url" not in feed_item


def test_only_one_parallel_approval_succeeds(client):
    _, faculty, course = setup_campus(client)
    first, _ = sign_in(client, "demo-student")
    second, _ = sign_in(client, "demo-second-student")
    call = create_call(client, faculty, course)
    applications = [apply(client, student, call).json()["id"] for student in (first, second)]
    with ThreadPoolExecutor(max_workers=2) as executor:
        decisions = list(executor.map(lambda item: approval(client, faculty, call, item), applications))
    assert sorted(decision.status_code for decision in decisions) == [200, 409]
    result = client.get(f"/v1/workshop-calls/{call}/applications", headers=faculty)
    assert sorted(item["status"] for item in result.json()) == ["approved", "not_selected"]
