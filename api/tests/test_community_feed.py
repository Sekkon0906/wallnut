from datetime import datetime, timedelta, timezone
from uuid import uuid4

from test_evidence import sample_photo
from test_pilot import apply, approval, client, create_call, setup_campus, sign_in
from wallnut.database import connect


def publish_event(client, actor, event_id):
    result = client.post('/v1/campus-events', headers=actor, json={
        'id': event_id, 'title': 'Encuentro del campus', 'description': 'Ven a compartir ejercicios y experiencias.',
        'category': 'campus', 'location': 'Plazoleta', 'capacity': 6,
        'starts_at': (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    })
    assert result.status_code == 201, result.text
    return result.json()


def test_feed_pagination_orders_all_sources_with_ties_and_new_arrivals(client):
    _, faculty, course = setup_campus(client)
    student, _ = sign_in(client, 'demo-student')
    call_id = create_call(client, faculty, course)
    shared_id = str(uuid4())
    assert client.post('/v1/posts', headers=student, data={'id': shared_id, 'body': 'Primera publicación.'}).is_success
    publish_event(client, student, shared_id)
    with connect() as db:
        db.execute('UPDATE workshop_calls SET id = %s WHERE id = %s', (shared_id, call_id))
        for table in ('social_posts', 'workshop_calls', 'campus_events'):
            db.execute(f"UPDATE {table} SET created_at = '2025-02-10 10:00:00+00' WHERE id = %s", (shared_id,))

    first = client.get('/v1/community-feed?limit=1', headers=student)
    assert first.status_code == 200, first.text
    assert first.headers['cache-control'] == 'private, no-store'
    first = first.json()
    assert [(item['kind'], item['id']) for item in first['items']] == [('post', shared_id)]
    assert client.post('/v1/posts', headers=student, data={'id': str(uuid4()), 'body': 'Una publicación más nueva.'}).is_success
    assert client.put(f'/v1/posts/{shared_id}', headers=student, data={'body': 'Texto corregido.'}).is_success
    found = first['items'][:]
    cursor = first['next_cursor']
    while cursor:
        page = client.get('/v1/community-feed', headers=student, params={'cursor': cursor, 'limit': 1})
        assert page.is_success, page.text
        page = page.json()
        found.extend(page['items'])
        cursor = page['next_cursor']
    assert [(item['kind'], item['id']) for item in found] == [('post', shared_id), ('event', shared_id), ('call', shared_id)]
    assert found[1]['content']['title'] == 'Encuentro del campus'
    assert found[2]['content']['id'] == shared_id
    assert client.get('/v1/community-feed?kind=post', headers=student).json()['items'][0]['id'] != shared_id


def test_feed_filters_preserve_cancelled_events_and_closed_call_state(client):
    _, faculty, course = setup_campus(client)
    student, _ = sign_in(client, 'demo-student')
    call_id = create_call(client, faculty, course)
    application = apply(client, student, call_id).json()['id']
    assert approval(client, faculty, call_id, application).is_success
    university_event = str(uuid4())
    student_event = str(uuid4())
    publish_event(client, faculty, university_event)
    publish_event(client, student, student_event)
    assert client.put(f'/v1/campus-events/{student_event}/cancel', headers=student).is_success
    assert client.post('/v1/posts', headers=faculty, data={'id': str(uuid4()), 'body': 'Noticia desde la Universidad.'}).is_success

    institutional = client.get('/v1/community-feed?origin=university', headers=student).json()['items']
    assert len(institutional) == 3 and all(item['institutional'] for item in institutional)
    call = next(item for item in institutional if item['kind'] == 'call')
    assert not call['content']['open'] and call['content']['my_application'] == 'approved'
    assert not call['content']['can_manage'] and call['content']['can_schedule']
    assert client.get(f'/v1/workshop-calls/{call_id}', headers=student).json() == call['content']
    events = client.get('/v1/community-feed?origin=students&kind=event', headers=student).json()['items']
    assert len(events) == 1 and events[0]['id'] == student_event and events[0]['content']['cancelled']
    assert not events[0]['content']['registration_open']
    assert client.get(f'/v1/campus-events/{student_event}', headers=student).json() == events[0]['content']
    assert client.get('/v1/community-feed?origin=students&kind=call', headers=student).json()['items'] == []
    assert client.get('/v1/community-feed').status_code == 401
    for query in ('limit=0', 'limit=31', 'origin=someone', 'kind=private', 'cursor=%24%24', 'cursor=YWJj'):
        assert client.get(f'/v1/community-feed?{query}', headers=student).status_code == 422


def test_feed_and_direct_post_link_apply_current_privacy_and_moderation(client):
    admin, _, _ = setup_campus(client)
    author, account = sign_in(client, 'demo-student')
    viewer, _ = sign_in(client, 'demo-second-student')
    post_id = str(uuid4())
    path = f'/v1/posts/{post_id}'
    result = client.post('/v1/posts', headers=author, data={'id': post_id, 'body': 'Foto del campus.'},
                         files={'photo': ('campus.png', sample_photo(), 'image/png')})
    assert result.status_code == 201, result.text
    assert client.put('/v1/my-campus-profile', headers=author, json={'visible': True}).is_success
    item = client.get('/v1/community-feed?kind=post', headers=viewer).json()['items'][0]['content']
    assert item['has_photo'] and item['author_profile_visible']
    assert account['email'] not in str(item) and 'photo' not in item and 'reflection' not in item
    assert client.get(path).status_code == 401
    assert client.get(path, headers=viewer).json() == item
    assert client.put('/v1/my-campus-profile', headers=author, json={'visible': False}).is_success
    assert not client.get('/v1/community-feed?kind=post', headers=viewer).json()['items'][0]['content']['author_profile_visible']

    assert client.put(f'{path}/moderation', headers=admin, json={'hidden': True, 'reason': 'Revisar la imagen adjunta.'}).is_success
    assert client.get('/v1/community-feed?kind=post', headers=viewer).json()['items'] == []
    assert client.get(path, headers=viewer).status_code == 404
    assert client.get(f'{path}/photo', headers=viewer).status_code == 404
    own = client.get('/v1/community-feed?kind=post', headers=author).json()['items']
    assert own[0]['content']['hidden']
    assert client.get(path, headers=author).json()['hidden']
    assert client.delete(path, headers=author).is_success
    assert client.get('/v1/community-feed?kind=post', headers=author).json()['items'] == []
    assert client.get(path, headers=author).status_code == 404
