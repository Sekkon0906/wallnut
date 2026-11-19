from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest

from test_evidence import record_attendance, workshop
from test_grade_redemptions import configure_course, redemption, review, rule, source_group
from test_pilot import client, sign_in
from test_wallet import allocation, approve, configure, evidence_path, faculty_context, upload
from test_workshop_agenda import change_input
from test_workshops import open_workshop, timetable, workshop_team
from wallnut import workshop_agenda
from wallnut.database import connect
from wallnut.notifications import record_notification


def notifications(client, headers, **params):
    result = client.get('/v1/notifications', headers=headers, params=params)
    assert result.is_success, result.text
    assert result.headers['cache-control'] == 'private, no-store'
    return result.json()


def cursor(entry):
    return {key: entry[key] for key in ('id', 'created_at')}


def test_agenda_notifies_current_participants_once_and_reading_is_private_and_bounded(client, workshop_team):
    faculty, course, facilitator, first, second = workshop_team
    identity = open_workshop(client, faculty, course, facilitator, capacity=3)
    path = f'/v1/workshops/{identity}'
    for student in (first, second):
        assert client.put(f'{path}/enrollment', headers=student).is_success
    data = change_input('rescheduled', **{**timetable(capacity=3), 'location': 'Salón 401'})
    assert client.put(f'{path}/agenda', headers=facilitator, json={**data, 'capacity': 1}).status_code == 409
    assert notifications(client, first)['entries'] == []
    assert client.delete(f'{path}/enrollment', headers=second).status_code == 204
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.put(f'{path}/agenda', headers=facilitator, json=data), range(2)))
    assert [result.status_code for result in results] == [204, 204]
    page = notifications(client, first)
    assert page['unread_count'] == 1 and len(page['entries']) == 1
    original = page['entries'][0]
    assert original['kind'] == 'workshop_rescheduled' and original['workshop_id'] == identity
    assert notifications(client, faculty)['unread_count'] == 1
    assert notifications(client, facilitator)['unread_count'] == notifications(client, second)['unread_count'] == 0
    read_path = f"/v1/notifications/{original['id']}/read"
    assert client.put(read_path, headers=second).status_code == 404
    assert client.put('/v1/notifications/read-through', headers=second, json=cursor(original)).status_code == 404
    marked = client.put(read_path, headers=first)
    assert marked.is_success and marked.json()['read_at']
    assert client.put(read_path, headers=first).json()['read_at'] == marked.json()['read_at']
    cancelled = client.put(f'{path}/agenda', headers=faculty, json=change_input('cancelled', revision=2))
    assert cancelled.status_code == 204, cancelled.text
    assert client.put('/v1/notifications/read-through', headers=first, json=cursor(original)).json()['unread_count'] == 1
    current = notifications(client, first, unread_only=True)
    assert len(current['entries']) == 1 and current['entries'][0]['kind'] == 'workshop_cancelled'
    through = client.put('/v1/notifications/read-through', headers=first, json=cursor(current['entries'][0]))
    assert through.is_success and through.json()['unread_count'] == 0
    assert notifications(client, first, unread_only=True)['entries'] == []
    count = client.get('/v1/notifications/unread-count', headers=first)
    assert count.json() == {'unread_count': 0} and count.headers['cache-control'] == 'private, no-store'
    assert notifications(client, second)['entries'] == []
    assert 'event_key' not in client.get('/v1/notifications', headers=first).text
    for endpoint in ('/v1/notifications', '/v1/notifications/unread-count'):
        assert client.get(endpoint).status_code == 401


def test_evidence_notifies_each_submission_and_review_without_private_content(client, workshop):
    faculty, student = workshop['faculty'], workshop['attendee']
    record_attendance(client, workshop)
    first = upload(client, workshop, 'attendee')
    assert [row['kind'] for row in notifications(client, faculty)['entries']] == ['evidence_submitted']
    body = {'decision': 'returned', 'comment': 'Comentario privado para corregir.', 'submitted_at': first['submitted_at']}
    path = f'{evidence_path(workshop, first)}/review'
    assert client.put(path, headers=workshop['unauthorized'], json=body).status_code == 403
    assert notifications(client, student)['entries'] == []
    for _ in range(2):
        assert client.put(path, headers=faculty, json=body).is_success
    returned = notifications(client, student)
    assert [row['kind'] for row in returned['entries']] == ['evidence_returned']
    corrected = upload(client, workshop, 'attendee')
    assert corrected['submitted_at'] != first['submitted_at']
    assert len(notifications(client, faculty)['entries']) == 2
    for _ in range(2):
        approve(client, workshop, corrected)
    page = notifications(client, student)
    assert [row['kind'] for row in page['entries']] == ['evidence_approved', 'evidence_returned']
    raw = client.get('/v1/notifications', headers=student).text
    assert all(secret not in raw for secret in (first['reflection'], body['comment'], 'photo', 'submitted_at', '@unibague'))


def test_grade_requests_and_decisions_notify_only_the_assigned_accounts_once(client, workshop):
    admin, faculty_id = faculty_context(client)
    faculty, student = workshop['faculty'], workshop['attendee']
    assert allocation(client, admin, faculty_id, 100).is_success
    configure(client, workshop, attendee_points=20)
    record_attendance(client, workshop)
    evidence = upload(client, workshop, 'attendee')
    approve(client, workshop, evidence)
    course = source_group(client, faculty)
    configure_course(client, workshop, course, rule([course]))
    request_id = str(uuid4())
    pending = redemption(client, student, course, 1, request_id).json()
    assert redemption(client, student, course, 1, request_id).json()['id'] == pending['id']
    requests = [entry for entry in notifications(client, faculty)['entries'] if entry['kind'] == 'redemption_requested']
    assert len(requests) == 1 and requests[0]['course_id'] == course and requests[0]['workshop_id'] is None
    for _ in range(2):
        assert review(client, faculty, course, pending['id'], 'approved').is_success
    second = redemption(client, student, course, 1).json()
    for _ in range(2):
        assert review(client, faculty, course, second['id'], 'rejected', 'Motivo privado del rechazo.').is_success
    results = [entry for entry in notifications(client, student)['entries'] if entry['kind'].startswith('redemption_')]
    assert [entry['kind'] for entry in results] == ['redemption_rejected', 'redemption_approved']
    assert notifications(client, admin)['entries'] == []
    assert notifications(client, workshop['facilitator'])['entries'] == []
    raw = client.get('/v1/notifications', headers=student).text
    assert all(value not in raw for value in ('Motivo privado', 'grade_before', 'grade_after', 'boost_milli', 'student_id'))


def test_notification_pagination_survives_ties_new_entries_and_unread_changes(client, workshop):
    student = workshop['attendee']
    with connect() as db:
        with db.transaction():
            with db.cursor() as cur:
                cur.executemany(
                    """INSERT INTO campus_notifications (id, account_id, event_key, kind, workshop_id, created_at)
                       VALUES (%s, %s, %s, 'workshop_rescheduled', %s, '2025-01-01 12:00:00+00')""",
                    [(UUID(int=index), workshop['student_id'], f'fixture:{index}', workshop['id']) for index in range(1, 55)],
                )
    first = notifications(client, student, limit=20)
    assert first['unread_count'] == 54 and len(first['entries']) == 20
    with connect() as db:
        record_notification(db, workshop['student_id'], 'fixture:new', 'workshop_cancelled', workshop_id=workshop['id'])
    rows = first['entries'][:]
    next_cursor = first['next_cursor']
    while next_cursor:
        page = notifications(client, student, limit=20, before=next_cursor['created_at'], before_id=next_cursor['id'])
        rows.extend(page['entries'])
        next_cursor = page['next_cursor']
    assert [row['id'] for row in rows] == [str(UUID(int=index)) for index in range(54, 0, -1)]
    assert client.put(f"/v1/notifications/{rows[0]['id']}/read", headers=student).is_success
    unread = notifications(client, student, unread_only=True, limit=50)
    assert unread['unread_count'] == 54 and all(row['read_at'] is None for row in unread['entries'])
    for query in ({'limit': 0}, {'limit': 51}, {'before_id': str(uuid4())}, {'before': '2025-01-01'}):
        assert client.get('/v1/notifications', headers=student, params=query).status_code == 422
    assert client.put('/v1/notifications/read-through', headers=student, json={**cursor(rows[0]), 'created_at': '2099-01-01T00:00:00Z'}).status_code == 404


def test_failed_workflow_rolls_back_both_agenda_and_notifications(client, workshop, monkeypatch):
    original = workshop_agenda.notify_agenda_change

    def interrupted(*args):
        original(*args)
        raise RuntimeError('Interrupción simulada antes del commit')

    monkeypatch.setattr(workshop_agenda, 'notify_agenda_change', interrupted)
    with pytest.raises(RuntimeError, match='Interrupción simulada'):
        client.put(f"/v1/workshops/{workshop['id']}/agenda", headers=workshop['faculty'],
                   json=change_input('cancelled'))
    assert notifications(client, workshop['attendee'])['entries'] == []
    with connect() as db:
        current = db.execute('SELECT schedule_revision, cancelled_at FROM workshops WHERE id = %s', (workshop['id'],)).fetchone()
    assert current == {'schedule_revision': 1, 'cancelled_at': None}
