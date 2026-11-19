from uuid import uuid4

from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from test_evidence import record_attendance, workshop
from test_pilot import client, sign_in
from test_wallet import approve, configure, evidence_path, upload, wallet
from wallnut.database import connect
from wallnut.main import create_app


PAYMENTS = '/v1/coin-payments'


def test_recent_requests_are_private_bounded_and_recoverable_with_a_new_session(client):
    recipient, person = sign_in(client, 'demo-student')
    payer, _ = sign_in(client, 'demo-second-student')
    other, _ = sign_in(client, 'demo-third-student')
    staff, _ = sign_in(client, 'demo-faculty')
    assert client.get(PAYMENTS).status_code == 401
    assert client.get(PAYMENTS, headers=staff).status_code == 403
    empty = client.get(PAYMENTS, headers=payer)
    assert empty.json() == [] and empty.headers['cache-control'] == 'private, no-store'
    ids = [str(uuid4()) for _ in range(12)]
    for payment_id in ids:
        created = client.post(PAYMENTS, headers=recipient, json={'id': payment_id, 'amount': 3})
        assert created.is_success, created.text
    unrelated = str(uuid4())
    assert client.post(PAYMENTS, headers=other, json={'id': unrelated, 'amount': 2}).is_success
    with connect() as db:
        db.execute("UPDATE coin_payment_requests SET expires_at = now() - interval '1 second' WHERE id = %s", (ids[-1],))

    new_session, _ = sign_in(client, 'demo-student')
    recent = client.get(PAYMENTS, headers=new_session)
    assert recent.headers['cache-control'] == 'private, no-store'
    rows = recent.json()
    assert len(rows) == 10 and {row['id'] for row in rows} == set(ids[1:-1])
    assert all(row['is_recipient'] and row['status'] == 'pending' and not row['paid_by_me'] for row in rows)
    assert person['email'] not in recent.text and unrelated not in recent.text
    recovered = client.get(f"{PAYMENTS}/{rows[0]['id']}", headers=new_session)
    assert recovered.json() == rows[0]
    assert client.get(f"{PAYMENTS}/{rows[0]['id']}", headers=payer).json()['can_pay']
    assert client.get(PAYMENTS, headers=payer).json() == []


def test_lost_payment_response_can_be_recovered_without_charging_twice(client, workshop):
    payer, recipient, faculty = (workshop[key] for key in ('attendee', 'facilitator', 'faculty'))
    configure(client, workshop)
    record_attendance(client, workshop)
    evidence = upload(client, workshop, 'attendee')
    approve(client, workshop, evidence)
    assert client.post(f'{evidence_path(workshop, evidence)}/goal', headers=faculty).is_success
    initial_payer = wallet(client, payer)['coins']
    initial_recipient = wallet(client, recipient)['coins']
    payment_id = str(uuid4())
    assert client.post(PAYMENTS, headers=recipient, json={'id': payment_id, 'amount': 3}).is_success
    path = f'{PAYMENTS}/{payment_id}'

    # Simulate a proxy losing the confirmation after the payment transaction committed.
    interrupted_app = create_app()

    @interrupted_app.middleware('http')
    async def lose_confirmation(request, call_next):
        response = await call_next(request)
        if request.url.path == f'{path}/pay' and response.status_code == 200:
            return JSONResponse({'detail': 'Confirmación interrumpida.'}, status_code=503)
        return response

    with TestClient(interrupted_app) as interrupted:
        result = interrupted.post(f'{path}/pay', headers=payer)
        assert result.status_code == 503

    with connect() as db:
        db.execute('UPDATE coin_payment_requests SET expires_at = paid_at WHERE id = %s', (payment_id,))
    recovered = client.get(path, headers=payer)
    assert recovered.status_code == 200, recovered.text
    result = recovered.json()
    assert result['status'] == 'paid' and result['paid_by_me'] and result['paid_at']
    assert not result['is_recipient'] and not result['can_pay']
    assert client.get(PAYMENTS, headers=payer).json() == [result]
    assert client.post(f'{path}/pay', headers=payer).json() == result
    assert wallet(client, payer)['coins'] == initial_payer - 3
    assert wallet(client, recipient)['coins'] == initial_recipient + 3

    receiver_view = client.get(PAYMENTS, headers=recipient).json()[0]
    assert receiver_view['is_recipient'] and not receiver_view['paid_by_me'] and receiver_view['status'] == 'paid'
    other, _ = sign_in(client, 'demo-third-student')
    assert client.get(PAYMENTS, headers=other).json() == []
    assert not client.get(path, headers=other).json()['paid_by_me']
