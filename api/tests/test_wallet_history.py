from datetime import datetime
from uuid import uuid4

from test_evidence import record_attendance, workshop
from test_grade_redemptions import configure_course, redemption, review, rule, source_group
from test_pilot import client, sign_in
from test_wallet import allocation, approve, configure, evidence_path, faculty_context, upload, wallet
from wallnut import wallet_history
from wallnut.database import connect


def earned(client, workshop, coins=40):
    admin, faculty_id = faculty_context(client)
    assert allocation(client, admin, faculty_id, 100).is_success
    configure(client, workshop, goal_coins=coins)
    record_attendance(client, workshop)
    evidence = upload(client, workshop, 'attendee')
    approve(client, workshop, evidence)
    path = evidence_path(workshop, evidence)
    assert client.post(f'{path}/goal', headers=workshop['faculty']).is_success
    return path


def payment(client, payer, recipient, amount=1):
    identity = str(uuid4())
    created = client.post('/v1/coin-payments', headers=recipient, json={'id': identity, 'amount': amount})
    assert created.is_success, created.text
    paid = client.post(f'/v1/coin-payments/{identity}/pay', headers=payer)
    assert paid.is_success, paid.text
    return identity


def history(client, headers, **params):
    result = client.get('/v1/wallet/history', headers=headers, params=params)
    assert result.is_success, result.text
    assert result.headers['cache-control'] == 'private, no-store'
    value = result.json()
    assert value['summary']['points_difference'] == value['summary']['coins_difference'] == 0
    return value


def test_history_explains_every_wallet_source_and_grade_reservations_privately(client, workshop):
    student, receiver, faculty = (workshop[key] for key in ('attendee', 'facilitator', 'faculty'))
    empty = history(client, receiver)
    assert empty['balances'] == {'points': 0, 'coins': 0, 'reserved_points': 0}
    assert empty['movements'] == [] and empty['next_cursor'] is None
    path = earned(client, workshop)
    assert client.post(f'{path}/convert', headers=student).is_success
    assert client.post('/v1/ardy-shop/cap-gold', headers=student).is_success
    assert client.post('/v1/ardy-nuts', headers=student, json={'id': str(uuid4())}).is_success
    payment(client, student, receiver, 7)
    payment(client, receiver, student, 2)
    course = source_group(client, faculty)
    configure_course(client, workshop, course, rule([course]))
    pending = redemption(client, student, course, 1)
    assert pending.status_code == 201, pending.text
    pending = pending.json()
    reserved = history(client, student)
    assert reserved['balances'] == {'points': 9, 'coins': 22, 'reserved_points': 4}
    assert {key: reserved['summary'][key] for key in ('credited_points', 'spent_points', 'credited_coins', 'spent_coins')} == {
        'credited_points': 13, 'spent_points': 0, 'credited_coins': 42, 'spent_coins': 20,
    }
    assert {row['kind'] for row in reserved['movements']} == {
        'evidence_reward', 'goal_coins', 'coin_conversion', 'ardy_purchase', 'ardy_nut', 'coin_sent', 'coin_received',
    }
    assert review(client, faculty, course, pending['id'], 'approved').is_success
    approved = history(client, student)
    assert approved['summary']['spent_points'] == 4
    assert approved['balances'] == {'points': 9, 'coins': 22, 'reserved_points': 0}
    assert approved['movements'][0]['kind'] == 'grade_redemption'
    second = redemption(client, student, course, 1).json()
    assert history(client, student)['balances']['reserved_points'] == 4
    assert review(client, faculty, course, second['id'], 'rejected', 'Revisa el ejercicio.').is_success
    released = history(client, student)
    assert released['balances'] == approved['balances'] and released['movements'] == approved['movements']
    assert released['summary']['spent_points'] == 4
    for currency, column in (('points', 'points'), ('coins', 'coins')):
        filtered = history(client, student, currency=currency)
        assert filtered['movements'] == [row for row in released['movements'] if row[column]]
        assert filtered['balances'] == released['balances']
        assert filtered['summary']['credited_points'] == 13
    legacy = wallet(client, student)
    assert released['balances'] == {key: legacy[key] for key in ('points', 'coins', 'reserved_points')}
    assert [(row['id'], row['kind']) for row in released['movements']] == [(row['id'], row['kind']) for row in legacy['movements']]
    private = client.get('/v1/wallet/history', headers=student).text
    assert all(field not in private for field in ('photo', 'reflection', 'grade_before', 'grade_after', 'student_id', '@unibague'))
    own = history(client, receiver)
    assert own['balances']['coins'] == 5 and {row['kind'] for row in own['movements']} == {'coin_received', 'coin_sent'}
    assert history(client, receiver, student_id=workshop['student_id'])['movements'] == own['movements']
    admin, _ = sign_in(client, 'demo-admin')
    for headers in (faculty, admin, workshop['unauthorized']):
        assert client.get('/v1/wallet/history', headers=headers).status_code == 403
    assert client.get('/v1/wallet/history').status_code == 401


def test_history_reaches_beyond_fifty_and_preserves_timestamp_and_cross_source_id_ties(client, workshop):
    student, receiver = workshop['attendee'], workshop['facilitator']
    earned(client, workshop, 100)
    payment_ids = [payment(client, student, receiver) for _ in range(53)]
    with connect() as db:
        goal = db.execute("SELECT id FROM wallet_movements WHERE kind = 'goal_coins'").fetchone()['id']
        db.execute('UPDATE coin_payment_requests SET id = %s WHERE id = %s', (goal, payment_ids[0]))
        db.execute("UPDATE coin_payment_requests SET paid_at = '2025-01-01 12:00:00+00'")
        db.execute("UPDATE wallet_movements SET created_at = '2025-01-01 12:00:00+00'")
    first = history(client, student, limit=20)
    assert len(first['movements']) == 20 and first['next_cursor']
    later = payment(client, student, receiver)
    rows = first['movements'][:]
    cursor = first['next_cursor']
    while cursor:
        page = history(client, student, limit=20, before=cursor['created_at'], before_id=cursor['id'], before_kind=cursor['kind'])
        rows.extend(page['movements'])
        cursor = page['next_cursor']
    assert len(rows) == len({(row['id'], row['kind']) for row in rows}) == 55
    assert not any(row['id'] == later for row in rows)
    assert len([row for row in rows if row['id'] == str(goal)]) == 2
    assert rows == sorted(rows, key=lambda row: (datetime.fromisoformat(row['created_at']), row['id'], row['kind']), reverse=True)
    refreshed = history(client, student, limit=50)
    assert refreshed['movements'][0]['id'] == later
    assert refreshed['balances']['coins'] == 46
    assert history(client, student, currency='points')['movements'][0]['kind'] == 'evidence_reward'
    for params in ({'limit': 0}, {'limit': 51}, {'currency': 'money'}, {'before_id': str(uuid4())},
                   {'before': '2025-01-01'}, {'before_kind': 'unknown'}):
        assert client.get('/v1/wallet/history', headers=student, params=params).status_code == 422


def test_history_summary_and_page_share_one_snapshot_during_a_payment(client, workshop, monkeypatch):
    student, receiver = workshop['attendee'], workshop['facilitator']
    earned(client, workshop, 20)
    original = wallet_history.wallet_totals
    completed = False

    def totals_then_pay(db, student_id):
        nonlocal completed
        totals = original(db, student_id)
        if not completed:
            completed = True
            payment(client, student, receiver, 5)
        return totals

    monkeypatch.setattr(wallet_history, 'wallet_totals', totals_then_pay)
    snapshot = history(client, student)
    assert completed and snapshot['balances']['coins'] == 20
    assert snapshot['summary']['spent_coins'] == 0
    assert not any(row['kind'] == 'coin_sent' for row in snapshot['movements'])
    current = history(client, student)
    assert current['balances']['coins'] == 15 and current['summary']['spent_coins'] == 5
    assert current['movements'][0]['kind'] == 'coin_sent'
