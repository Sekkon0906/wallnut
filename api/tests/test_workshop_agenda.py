from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from test_evidence import sample_photo
from test_pilot import client, sign_in
from test_workshops import agenda_entry, open_workshop, start_workshops, timetable, workshop_team
from wallnut.database import connect


def change_input(kind, revision=1, **details):
    return {"request_id": str(uuid4()), "kind": kind, "revision": revision,
            "reason": "Cambio de disponibilidad del salón.", **details}


def test_reschedule_keeps_registrations_and_records_the_previous_time(client, workshop_team):
    faculty, course, facilitator, first, second = workshop_team
    workshop_id = open_workshop(client, faculty, course, facilitator, capacity=3)
    endpoint = f"/v1/workshops/{workshop_id}"
    original = agenda_entry(client, first, workshop_id)
    for student in (first, second):
        assert client.put(f"{endpoint}/enrollment", headers=student).status_code == 201

    intended = timetable(capacity=2)
    intended["location"] = "Salón 402"
    schedule = change_input("rescheduled", **intended)
    assert client.put(f"{endpoint}/agenda", headers=first, json=schedule).status_code == 403
    assert client.put(f"{endpoint}/agenda", headers=faculty, json={**schedule, "capacity": 1}).status_code == 409
    modified = client.put(f"{endpoint}/agenda", headers=facilitator, json=schedule)
    assert modified.status_code == 204, modified.text
    assert client.put(f"{endpoint}/agenda", headers=facilitator, json=schedule).status_code == 204
    assert client.put(f"{endpoint}/agenda", headers=facilitator,
                      json={**schedule, "location": "Salón 403"}).status_code == 409

    current = agenda_entry(client, first, workshop_id)
    assert current["enrolled"] and current["enrolled_count"] == current["capacity"] == 2
    assert current["schedule_revision"] == 2 and current["schedule_change"] == "rescheduled"
    assert current["location"] == "Salón 402" and current["schedule_notice"] == schedule["reason"]
    assert current["previous_starts_at"] == original["starts_at"]
    assert client.put(f"{endpoint}/agenda", headers=faculty, json=change_input("cancelled")).status_code == 409
    start_workshops(workshop_id)
    assert client.put(f"{endpoint}/agenda", headers=faculty,
                      json=change_input("cancelled", revision=2)).status_code == 409


def test_cancelled_workshop_remains_in_agenda_and_blocks_activity(client, workshop_team):
    faculty, course, facilitator, first, second = workshop_team
    admin, _ = sign_in(client, "demo-admin")
    workshop_id = open_workshop(client, faculty, course, facilitator)
    endpoint = f"/v1/workshops/{workshop_id}"
    assert client.put(f"{endpoint}/enrollment", headers=first).is_success
    cancel = change_input("cancelled")
    assert client.put(f"{endpoint}/agenda", headers=facilitator, json=cancel).status_code == 403
    assert client.put(f"{endpoint}/agenda", headers=admin, json=cancel).status_code == 204
    assert client.put(f"{endpoint}/agenda", headers=admin, json=cancel).status_code == 204
    current = agenda_entry(client, first, workshop_id)
    assert current["cancelled_at"] and current["enrolled"] and current["enrolled_count"] == 1
    assert current["schedule_notice"] == cancel["reason"]
    assert current["schedule_revision"] == 2 and current["schedule_change"] == "cancelled"
    assert client.put(f"{endpoint}/enrollment", headers=second).status_code == 409
    assert client.delete(f"{endpoint}/enrollment", headers=first).status_code == 409
    assert client.put(f"{endpoint}/economy", headers=faculty,
                      json={"attendee_points": 2, "facilitator_points": 3}).status_code == 409

    # Simula que ya llegó el horario original sin modificar el reloj del servidor.
    with connect() as db:
        db.execute(
            """
            UPDATE workshops SET starts_at = now() - interval '1 minute',
              cancelled_at = now() - interval '2 minutes', ends_at = now() + interval '1 hour'
            WHERE id = %s
            """,
            (workshop_id,),
        )
    assert client.post(f"{endpoint}/attendance-code", headers=faculty).status_code == 409
    assert client.post(f"{endpoint}/attendance", headers=first, json={"code": "VALID234"}).status_code == 409
    evidence = client.post(
        f"{endpoint}/evidence", headers=facilitator, data={"reflection": "Material del taller."},
        files={"photo": ("evidencia.png", sample_photo(), "image/png")},
    )
    assert evidence.status_code == 409 and "cancelado" in evidence.json()["detail"]


def test_concurrent_schedule_changes_accept_one_revision(client, workshop_team):
    faculty, course, facilitator, first, _ = workshop_team
    workshop_id = open_workshop(client, faculty, course, facilitator)
    endpoint = f"/v1/workshops/{workshop_id}/agenda"
    changes = (change_input("cancelled"), change_input("rescheduled", **{**timetable(), "location": "Salón 302"}))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda data: client.put(endpoint, headers=faculty, json=data), changes))
    assert sorted(response.status_code for response in results) == [204, 409]
    assert agenda_entry(client, first, workshop_id)["schedule_revision"] == 2
    with connect() as db:
        assert db.execute("SELECT count(*) AS total FROM workshop_agenda_changes WHERE workshop_id = %s",
                          (workshop_id,)).fetchone()["total"] == 1
