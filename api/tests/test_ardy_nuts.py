from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from test_evidence import record_attendance, workshop
from test_pilot import client
from test_wallet import approve, configure, evidence_path, upload, wallet
from wallnut import ardy_nuts


def test_nut_payment_and_three_recoverable_taps(client, workshop, monkeypatch):
    student, other, faculty = (workshop[key] for key in ("attendee", "facilitator", "faculty"))
    url = "/v1/ardy-nuts"
    body = {"id": str(uuid4())}
    assert client.get(url).status_code == 401
    assert client.post(url, headers=faculty, json=body).status_code == 403
    assert client.post(url, headers=student, json=body).status_code == 409

    configure(client, workshop, goal_coins=16)
    record_attendance(client, workshop)
    evidence = upload(client, workshop, "attendee")
    approve(client, workshop, evidence)
    assert client.post(f"{evidence_path(workshop, evidence)}/goal", headers=faculty).is_success
    shop = client.get(url, headers=student).json()
    assert shop == {"price": 4, "coins": 16, "odds": ardy_nuts.RARITY_WEIGHTS, "latest": None}
    monkeypatch.setattr(ardy_nuts, "randbelow", lambda total: 0)

    def buy():
        result = client.post(url, headers=student, json=body)
        assert result.is_success, result.text
        return result.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, retry = executor.submit(buy), executor.submit(buy)
        assert first.result() == retry.result() == {"id": body["id"], "taps": 0, "rarity": None, "reward": None}
    assert client.post(url, headers=student, json={"id": str(uuid4())}).status_code == 409
    first_wallet = wallet(client, student)
    assert first_wallet["coins"] == 12
    assert first_wallet["movements"][0]["kind"] == "ardy_nut"
    assert first_wallet["movements"][0]["coins"] == -4

    endpoint = f"{url}/{body['id']}/tap"
    assert client.put(endpoint, headers=other, json={"step": 1}).status_code == 404
    assert client.put(endpoint, headers=student, json={"step": 2}).status_code == 409
    cracked = client.put(endpoint, headers=student, json={"step": 1}).json()
    assert cracked["taps"] == 1 and cracked["rarity"] == "normal" and cracked["reward"] is None
    assert client.get(url, headers=student).json()["latest"] == cracked
    assert client.put(endpoint, headers=student, json={"step": 1}).json() == cracked
    assert client.put(endpoint, headers=student, json={"step": 2}).json()["reward"] is None
    assert all(not item.get("rarity") for item in client.get("/v1/ardy-shop", headers=student).json())

    opened = client.put(endpoint, headers=student, json={"step": 3}).json()
    assert opened["taps"] == 3 and opened["reward"]["owned"]
    assert client.put(endpoint, headers=student, json={"step": 3}).json() == opened
    assert buy() == opened
    assert wallet(client, student)["coins"] == 12
    reward = opened["reward"]
    assert reward in client.get("/v1/ardy-shop", headers=student).json()
    profile = client.get("/v1/my-ardy", headers=student).json()
    profile["avatar"][reward["slot"]] = reward["value"]
    assert client.put("/v1/my-ardy", headers=student, json=profile).json() == profile
    assert client.put("/v1/my-ardy", headers=other, json=profile).status_code == 403

    second_id = str(uuid4())
    assert client.post(url, headers=student, json={"id": second_id}).is_success
    for step in range(1, 4):
        response = client.put(f"{url}/{second_id}/tap", headers=student, json={"step": step})
        assert response.is_success, response.text
    assert response.json()["reward"]["id"] != reward["id"]
    assert client.get(url, headers=student).json()["odds"] == {**ardy_nuts.RARITY_WEIGHTS, "normal": 0}
