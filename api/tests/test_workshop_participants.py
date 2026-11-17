from test_evidence import record_attendance, submit, workshop
from test_pilot import client, sign_in
from test_workshop_agenda import change_input


def test_teacher_roster_tracks_check_in_and_evidence_without_private_content(client, workshop):
    url = f"/v1/workshops/{workshop['id']}/participants"
    admin, _ = sign_in(client, "demo-admin")
    _, student = sign_in(client, "demo-student")
    assert client.get(url).status_code == 401
    for actor in (admin, workshop["attendee"], workshop["facilitator"], workshop["unauthorized"]):
        assert client.get(url, headers=actor).status_code == 403

    roster = client.get(url, headers=workshop["faculty"])
    assert roster.headers["cache-control"] == "private, no-store"
    assert roster.json() == [{
        "student_id": student["id"], "display_name": student["display_name"],
        "checked_in_at": None, "evidence_status": None,
    }]

    record_attendance(client, workshop)
    evidence = submit(client, workshop, "attendee", reflection="Mi reflexión privada.")
    assert evidence.status_code == 201, evidence.text
    context = evidence.json()
    submitted = client.get(url, headers=workshop["faculty"])
    assert submitted.json()[0]["checked_in_at"]
    assert submitted.json()[0]["evidence_status"] == "submitted"
    assert "Mi reflexión privada" not in submitted.text and student["email"] not in submitted.text

    review = client.put(f"{workshop['url']}/{context['id']}/review", headers=workshop["faculty"],
                        json={"decision": "approved", "submitted_at": context["submitted_at"]})
    assert review.is_success, review.text
    assert client.get(url, headers=workshop["faculty"]).json()[0]["evidence_status"] == "approved"


def test_cancelled_workshop_preserves_the_roster_for_the_assigned_teacher(client, workshop):
    url = f"/v1/workshops/{workshop['id']}"
    assert client.put(f"{url}/agenda", headers=workshop["faculty"], json=change_input("cancelled")).is_success
    roster = client.get(f"{url}/participants", headers=workshop["faculty"])
    assert roster.is_success and len(roster.json()) == 1
    assert not roster.json()[0]["checked_in_at"]
