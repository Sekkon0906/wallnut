from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from test_evidence import record_attendance, workshop
from test_pilot import client, sign_in
from test_wallet import allocation, approve, configure, evidence_path, faculty_context, upload
from wallnut.database import connect


def test_ledger_links_allocations_rewards_and_conversions_without_private_student_data(client, workshop):
    admin, faculty_id = faculty_context(client)
    path = f'/v1/faculty-budgets/{faculty_id}/ledger'
    request_id = str(uuid4())
    first = allocation(client, admin, faculty_id, 100, request_id)
    assert first.is_success, first.text
    assert allocation(client, admin, faculty_id, 100, request_id).json() == first.json()
    configure(client, workshop)
    record_attendance(client, workshop)
    evidence = upload(client, workshop, 'attendee')
    approve(client, workshop, evidence)
    evidence_url = evidence_path(workshop, evidence)
    assert client.post(f'{evidence_url}/goal', headers=workshop['faculty']).is_success
    assert client.post(f'{evidence_url}/convert', headers=workshop['attendee']).is_success

    result = client.get(path, headers=admin)
    assert result.is_success, result.text
    assert result.headers['cache-control'] == 'private, no-store'
    ledger = result.json()
    assert (ledger['allocated_points'], ledger['awarded_points'], ledger['converted_points']) == (100, 7, 6)
    assert ledger['available_points'] == 87 and ledger['difference'] == 0
    assert [(row['kind'], row['points']) for row in ledger['entries']] == [
        ('coin_conversion', -6), ('evidence_reward', -7), ('allocation', 100),
    ]
    assert ledger['entries'][0]['course'] == 'Cálculo III'
    assert ledger['entries'][0]['workshop'] == 'Se busca tallerista'
    assert ledger['entries'][2]['actor'] == 'Equipo Campus'
    assert ledger['next_cursor'] is None
    assert workshop['student_id'] not in result.text and evidence['reflection'] not in result.text
    assert 'photo' not in result.text and 'grade' not in result.text
    own = client.get(path, headers=workshop['faculty'])
    assert own.is_success and own.json()['entries'] == ledger['entries']
    assert client.get(path).status_code == 401
    for other in ('attendee', 'facilitator', 'unauthorized'):
        assert client.get(path, headers=workshop[other]).status_code == 403
    other_teacher, identity = sign_in(client, 'external-staff')
    assert client.post('/v1/faculty', headers=admin, json={'email': identity['email']}).is_success
    assert client.get(path, headers=other_teacher).status_code == 403
    empty = client.get(f"/v1/faculty-budgets/{identity['id']}/ledger", headers=other_teacher)
    assert empty.is_success and empty.json()['entries'] == [] and empty.json()['difference'] == 0
    assert client.get(f'/v1/faculty-budgets/{uuid4()}/ledger', headers=admin).status_code == 404


def test_ledger_pagination_preserves_a_tie_and_concurrent_allocation_retries(client, workshop):
    admin, faculty_id = faculty_context(client)
    path = f'/v1/faculty-budgets/{faculty_id}/ledger'
    request_id = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: allocation(client, admin, faculty_id, 10, request_id), range(2)))
    assert all(result.status_code == 201 for result in results)
    assert results[0].json()['id'] == results[1].json()['id']
    assert allocation(client, admin, faculty_id, 20).is_success
    with connect() as db:
        db.execute("UPDATE point_allocations SET created_at = '2025-02-10 10:00:00+00' WHERE faculty_id = %s", (faculty_id,))
    first = client.get(path, headers=admin, params={'limit': 1})
    assert first.is_success, first.text
    first = first.json()
    cursor = first['next_cursor']
    assert first['allocated_points'] == first['available_points'] == 30
    assert cursor and first['difference'] == 0
    assert allocation(client, admin, faculty_id, 5).is_success
    second = client.get(path, headers=admin, params={
        'limit': 1, 'before': cursor['created_at'], 'before_id': cursor['id'], 'before_kind': cursor['kind'],
    })
    assert second.is_success, second.text
    second = second.json()
    assert len(second['entries']) == 1 and second['entries'][0]['id'] != first['entries'][0]['id']
    assert second['next_cursor'] is None and second['difference'] == 0
    assert second['allocated_points'] == second['available_points'] == 35
    refreshed = client.get(path, headers=admin).json()
    assert refreshed['entries'][0]['points'] == 5 and len(refreshed['entries']) == 3
    for query in ('limit=0', 'limit=51', 'before_id=not-a-uuid', f'before_id={uuid4()}', 'before=2025-01-01'):
        assert client.get(f'{path}?{query}', headers=admin).status_code == 422


def test_ledger_reports_a_balance_difference_without_changing_the_budget(client, workshop):
    admin, faculty_id = faculty_context(client)
    assert allocation(client, admin, faculty_id, 10).is_success
    with connect() as db:
        db.execute('UPDATE faculty_point_budgets SET available_points = 11 WHERE faculty_id = %s', (faculty_id,))
    result = client.get(f'/v1/faculty-budgets/{faculty_id}/ledger', headers=admin)
    assert result.is_success, result.text
    assert result.json()['difference'] == -1 and result.json()['available_points'] == 11
    with connect() as db:
        budget = db.execute('SELECT available_points FROM faculty_point_budgets WHERE faculty_id = %s', (faculty_id,)).fetchone()
        assert budget['available_points'] == 11
