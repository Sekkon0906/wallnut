from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from test_evidence import record_attendance, workshop
from test_pilot import client
from test_wallet import approve, configure, evidence_path, upload, wallet
from wallnut.database import connect


def test_coin_payment_and_shop_share_the_same_balance(client, workshop):
    payer, receiver, faculty = (workshop[key] for key in ("attendee", "facilitator", "faculty"))
    configure(client, workshop)
    record_attendance(client, workshop)
    evidence = upload(client, workshop, "attendee")
    approve(client, workshop, evidence)
    assert client.post(f"{evidence_path(workshop, evidence)}/goal", headers=faculty).is_success

    profile = client.get("/v1/my-ardy", headers=payer).json()
    profile["avatar"]["headwear"] = "gold_cap"
    assert client.put("/v1/my-ardy", headers=payer, json=profile).status_code == 403
    item = "/v1/ardy-shop/cap-gold"
    pay = "/v1/coin-payments"
    request = {"id": str(uuid4()), "amount": 5}
    assert client.post(pay, headers=faculty, json=request).status_code == 403
    created = client.post(pay, headers=receiver, json=request)
    assert created.is_success, created.text
    assert created.json()["status"] == "pending"
    assert client.post(pay, headers=receiver, json=request).json() == created.json()
    url = f"{pay}/{request['id']}"
    assert client.post(f"{url}/pay", headers=receiver).status_code == 409
    assert client.get(url, headers=payer).json()["can_pay"]

    actions = (item, f"{url}/pay")
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda path: client.post(path, headers=payer), actions))
    assert sorted(result.status_code for result in results) == [200, 409]
    if results[0].is_success:
        assert client.post(item, headers=payer).is_success
        assert wallet(client, payer)["coins"] == 4
        assert client.put("/v1/my-ardy", headers=payer, json=profile).is_success
        assert wallet(client, payer)["movements"][0]["kind"] == "ardy_purchase"
    else:
        assert client.post(f"{url}/pay", headers=payer).is_success
        assert wallet(client, payer)["coins"] == 3
        assert wallet(client, receiver)["coins"] == 5
        assert wallet(client, receiver)["movements"][0]["kind"] == "coin_received"
        assert client.post(item, headers=receiver).is_success
        assert wallet(client, receiver)["coins"] == 1

    previous_payer, previous_receiver = (wallet(client, account)["coins"] for account in (payer, receiver))
    second = {"id": str(uuid4()), "amount": 1}
    assert client.post(pay, headers=receiver, json=second).is_success
    second_url = f"{pay}/{second['id']}/pay"
    first_attempt = client.post(second_url, headers=payer)
    assert first_attempt.is_success, first_attempt.text
    assert client.post(second_url, headers=payer).json() == first_attempt.json()
    assert wallet(client, payer)["coins"] == previous_payer - 1
    assert wallet(client, receiver)["coins"] == previous_receiver + 1

    expired = {"id": str(uuid4()), "amount": 1}
    assert client.post(pay, headers=receiver, json=expired).is_success
    with connect() as db:
        db.execute("UPDATE coin_payment_requests SET expires_at = now() - interval '1 second' WHERE id = %s",
                   (expired["id"],))
    expired_url = f"{pay}/{expired['id']}"
    assert client.get(expired_url, headers=payer).json()["status"] == "expired"
    assert client.post(f"{expired_url}/pay", headers=payer).status_code == 409
