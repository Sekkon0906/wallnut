from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from test_pilot import apply, approval, client, create_call, sign_in, setup_campus
from wallnut.database import connect


@pytest.fixture
def workshop_team(client, monkeypatch):
    verify_identity = client.app.state.verify_identity

    def with_third_student(credential):
        if credential == "third-student":
            return {
                **verify_identity("demo-student"),
                "sub": credential,
                "email": "luisa.piloto@estudiantesunibague.edu.co",
                "name": "Luisa Piloto",
            }
        return verify_identity(credential)

    monkeypatch.setattr(client.app.state, "verify_identity", with_third_student)
    _, faculty, course = setup_campus(client)
    facilitator, _ = sign_in(client, "demo-second-student")
    maria, _ = sign_in(client, "demo-student")
    luisa, _ = sign_in(client, "third-student")
    return faculty, course, facilitator, maria, luisa


def timetable(capacity=10):
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    return {
        "starts_at": start.isoformat(),
        "ends_at": (start + timedelta(hours=1)).isoformat(),
        "capacity": capacity,
        "location": "Salón 201",
    }


def propose_as_facilitator(client, faculty, course, facilitator):
    call = create_call(client, faculty, course)
    submission = apply(client, facilitator, call)
    assert submission.status_code == 201, submission.text
    return call, submission.json()["id"]


def open_workshop(client, faculty, course, facilitator, capacity=10):
    call, submission = propose_as_facilitator(client, faculty, course, facilitator)
    assert approval(client, faculty, call, submission).status_code == 200
    scheduled = client.post(
        f"/v1/workshop-calls/{call}/workshop", headers=faculty, json=timetable(capacity)
    )
    assert scheduled.status_code == 201, scheduled.text
    return scheduled.json()["id"]


def agenda_entry(client, person, workshop_id):
    result = client.get("/v1/workshops", headers=person)
    assert result.status_code == 200, result.text
    return next(workshop for workshop in result.json() if workshop["id"] == workshop_id)


def start_workshops(*workshop_ids):
    with connect() as db:
        db.execute(
            """
            UPDATE workshops
            SET starts_at = now() - interval '1 minute', ends_at = now() + interval '30 minutes'
            WHERE id IN (SELECT unnest(%s::uuid[]))
            """,
            (list(workshop_ids),),
        )


def test_only_the_faculty_or_selected_facilitator_can_schedule(client, workshop_team):
    faculty, course, facilitator, maria, _ = workshop_team
    call, submission = propose_as_facilitator(client, faculty, course, facilitator)
    endpoint = f"/v1/workshop-calls/{call}/workshop"
    schedule = timetable()

    assert client.post(endpoint, headers=faculty, json=schedule).status_code == 409
    assert approval(client, faculty, call, submission).status_code == 200
    assert client.post(endpoint, headers=maria, json=schedule).status_code == 403
    assert client.get("/v1/workshop-calls", headers=facilitator).json()[0]["can_schedule"]

    result = client.post(endpoint, headers=facilitator, json=schedule)
    assert result.status_code == 201, result.text
    workshop = agenda_entry(client, facilitator, result.json()["id"])
    assert workshop["call_id"] == call
    assert workshop["course"] == "Cálculo III"
    assert workshop["location"] == "Salón 201"
    assert workshop["facilitator_name"] == "Mateo Piloto"
    assert workshop["is_facilitator"]
    assert not client.get("/v1/workshop-calls", headers=facilitator).json()[0]["can_schedule"]
    assert client.post(endpoint, headers=faculty, json=schedule).status_code == 409


def test_capacity_survives_concurrent_signups_and_cancellation(client, workshop_team):
    faculty, course, facilitator, maria, luisa = workshop_team
    workshop_id = open_workshop(client, faculty, course, facilitator, capacity=1)
    endpoint = f"/v1/workshops/{workshop_id}/enrollment"
    assert 400 <= client.put(endpoint, headers=facilitator).status_code < 500

    students = [maria, luisa]
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda student: client.put(endpoint, headers=student), students))
    assert sorted(response.status_code for response in responses) == [201, 409]

    winner_index = next(i for i, response in enumerate(responses) if response.is_success)
    enrolled, waiting = students[winner_index], students[1 - winner_index]
    assert client.put(endpoint, headers=enrolled).is_success
    assert agenda_entry(client, enrolled, workshop_id)["enrolled"]
    assert agenda_entry(client, waiting, workshop_id)["enrolled_count"] == 1
    assert client.delete(endpoint, headers=enrolled).status_code == 204
    assert client.put(endpoint, headers=waiting).status_code == 201
    assert not agenda_entry(client, enrolled, workshop_id)["enrolled"]


def test_attendance_code_is_workshop_bound_and_requires_enrollment(client, workshop_team):
    faculty, course, facilitator, maria, luisa = workshop_team
    workshop_id = open_workshop(client, faculty, course, facilitator)
    other_id = open_workshop(client, faculty, course, facilitator)
    endpoint = f"/v1/workshops/{workshop_id}"
    other_endpoint = f"/v1/workshops/{other_id}"
    assert client.put(f"{endpoint}/enrollment", headers=maria).status_code == 201
    assert client.put(f"{other_endpoint}/enrollment", headers=maria).status_code == 201
    assert client.post(f"{endpoint}/attendance-code", headers=faculty).status_code == 409
    start_workshops(workshop_id, other_id)
    assert client.put(f"{endpoint}/enrollment", headers=luisa).status_code == 409
    assert client.post(f"{endpoint}/attendance-code", headers=maria).status_code == 403
    assert agenda_entry(client, faculty, workshop_id)["can_manage"]
    assert agenda_entry(client, facilitator, workshop_id)["can_issue_code"]

    first_code = client.post(f"{endpoint}/attendance-code", headers=facilitator)
    assert first_code.status_code < 300, first_code.text
    initial = first_code.json()
    assert initial["qr_value"] == f"wallnut:attendance:{workshop_id}:{initial['code']}"
    assert client.post(f"{other_endpoint}/attendance", headers=maria, json={
        "code": initial["code"],
    }).status_code == 400
    assert client.post(f"{endpoint}/attendance", headers=luisa, json={
        "code": initial["code"],
    }).status_code == 403

    rotation = client.post(f"{endpoint}/attendance-code", headers=faculty)
    assert rotation.status_code < 300, rotation.text
    assert client.post(f"{endpoint}/attendance", headers=maria, json={
        "code": initial["code"],
    }).status_code == 400
    with connect() as db:
        db.execute(
            """
            UPDATE workshops SET attendance_code_expires_at = now() - interval '1 second'
            WHERE id = %s
            """,
            (workshop_id,),
        )
    assert client.post(f"{endpoint}/attendance", headers=maria, json={
        "code": rotation.json()["code"],
    }).status_code == 400
    code = client.post(f"{endpoint}/attendance-code", headers=faculty).json()["code"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        attempts = list(executor.map(
            lambda _: client.post(f"{endpoint}/attendance", headers=maria, json={"code": code}),
            range(2),
        ))
    assert all(result.is_success for result in attempts), [result.text for result in attempts]
    records = [result.json() for result in attempts]
    assert sorted(record["already_recorded"] for record in records) == [False, True]
    assert records[0]["checked_in_at"] == records[1]["checked_in_at"]
    assert agenda_entry(client, maria, workshop_id)["attended"]
    assert not agenda_entry(client, maria, other_id)["attended"]
