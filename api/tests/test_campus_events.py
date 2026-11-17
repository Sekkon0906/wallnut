from datetime import datetime, timedelta, timezone
from uuid import uuid4

from test_pilot import client, setup_campus, sign_in


def test_students_and_university_publish_events_with_limited_capacity(client):
    admin, faculty, _ = setup_campus(client)
    maria, _ = sign_in(client, "demo-student")
    mateo, _ = sign_in(client, "demo-second-student")
    staff, _ = sign_in(client, "external-staff")
    url = "/v1/campus-events"
    event = {
        "id": str(uuid4()), "title": "Torneo de ajedrez", "description": "Partidas amistosas entre estudiantes.",
        "category": "tournament", "location": "Biblioteca", "capacity": 2,
        "starts_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }
    assert client.post(url, headers=staff, json=event).status_code == 403
    created = client.post(url, headers=maria, json=event)
    assert created.status_code == 201, created.text
    assert created.json()["mine"] and not created.json()["institutional"]
    assert client.post(url, headers=maria, json=event).json() == created.json()
    university = client.post(url, headers=faculty, json={**event, "id": str(uuid4())}).json()
    assert university["institutional"]
    assert len(client.get(url, headers=mateo).json()) == 2
    enrollment = f"{url}/{event['id']}/enrollment"
    assert client.put(enrollment, headers=maria).json()["attendees"] == 1
    assert client.put(enrollment, headers=mateo).json()["attendees"] == 2
    assert client.put(enrollment, headers=mateo).json()["attendees"] == 2
    assert client.delete(enrollment, headers=mateo).json()["attendees"] == 1
    cancel = f"{url}/{event['id']}/cancel"
    assert client.put(cancel, headers=mateo).status_code == 403
    assert client.put(cancel, headers=admin).json()["cancelled"]
    assert client.put(enrollment, headers=mateo).status_code == 409
