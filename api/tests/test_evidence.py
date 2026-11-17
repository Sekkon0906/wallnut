from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest
from PIL import Image, PngImagePlugin

from test_pilot import apply, approval, client, create_call, setup_campus, sign_in
from wallnut.database import connect


@pytest.fixture
def workshop(client):
    _, faculty, course = setup_campus(client)
    facilitator, _ = sign_in(client, "demo-second-student")
    attendee, student = sign_in(client, "demo-student")
    unauthorized, _ = sign_in(client, "external-staff")
    call = create_call(client, faculty, course)
    application = apply(client, facilitator, call).json()["id"]
    assert approval(client, faculty, call, application).status_code == 200
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    scheduled = client.post(f"/v1/workshop-calls/{call}/workshop", headers=faculty, json={
        "starts_at": start.isoformat(), "ends_at": (start + timedelta(hours=1)).isoformat(),
        "location": "Salón de cálculo", "capacity": 12,
    })
    assert scheduled.status_code == 201, scheduled.text
    workshop_id = scheduled.json()["id"]
    assert client.put(f"/v1/workshops/{workshop_id}/enrollment", headers=attendee).status_code == 201
    return {
        "id": workshop_id, "url": f"/v1/workshops/{workshop_id}/evidence", "faculty": faculty,
        "facilitator": facilitator, "attendee": attendee, "student_id": student["id"],
        "unauthorized": unauthorized,
    }


def start_workshop(workshop):
    with connect() as db:
        db.execute(
            "UPDATE workshops SET starts_at = now() - interval '2 minutes' WHERE id = %s",
            (workshop["id"],),
        )


def record_attendance(client, workshop):
    start_workshop(workshop)
    url = f"/v1/workshops/{workshop['id']}"
    code = client.post(f"{url}/attendance-code", headers=workshop["faculty"]).json()["code"]
    checked_in = client.post(f"{url}/attendance", headers=workshop["attendee"], json={"code": code})
    assert checked_in.status_code == 200, checked_in.text


def sample_photo():
    output = BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("location", "private metadata")
    Image.new("RGBA", (2000, 1200), (30, 65, 110, 240)).save(output, "PNG", pnginfo=metadata)
    return output.getvalue()


def submit(client, workshop, role, *, photo=None, reflection="Resolví las dos primeras series."):
    return client.post(workshop["url"], headers=workshop[role], data={"reflection": reflection},
                       files={"photo": ("cuaderno.png", photo or sample_photo(), "image/png")})


def test_evidence_access_and_photo_sanitization(client, workshop):
    assert submit(client, workshop, "attendee").status_code == 409
    assert submit(client, workshop, "facilitator").status_code == 409
    record_attendance(client, workshop)

    rejected = submit(client, workshop, "attendee", photo=b"<html>not an image</html>")
    assert rejected.status_code == 415
    uploaded = submit(client, workshop, "attendee", reflection="  Resolví el ejercicio.  ")
    assert uploaded.status_code == 201, uploaded.text
    evidence = uploaded.json()
    assert evidence["student_id"] == workshop["student_id"]
    assert evidence["status"] == "submitted"
    assert evidence["reflection"] == "Resolví el ejercicio."
    assert evidence["photo_content_type"] == "image/jpeg"
    assert submit(client, workshop, "attendee").status_code == 409

    url = workshop["url"]
    assert client.get(url, headers=workshop["facilitator"]).json() == []
    assert client.get(url, headers=workshop["unauthorized"]).status_code == 403
    assert client.get(url, headers=workshop["attendee"]).json() == [evidence]
    assert client.get(url, headers=workshop["faculty"]).json() == [evidence]

    image_url = f"{url}/{evidence['id']}/photo"
    assert client.get(image_url).status_code == 401
    assert client.get(image_url, headers=workshop["facilitator"]).status_code == 404
    photo = client.get(image_url, headers=workshop["faculty"])
    assert photo.headers["cache-control"] == "private, no-store"
    assert photo.headers["content-type"] == "image/jpeg"
    with Image.open(BytesIO(photo.content)) as decoded:
        assert decoded.size == (1600, 960)
        assert "location" not in decoded.info and not decoded.getexif()

    assert submit(client, workshop, "facilitator").status_code == 201
    assert len(client.get(url, headers=workshop["faculty"]).json()) == 2


def test_evidence_return_resubmit_and_approval(client, workshop):
    record_attendance(client, workshop)
    first = submit(client, workshop, "attendee").json()
    review_url = f"{workshop['url']}/{first['id']}/review"
    faculty = workshop["faculty"]
    assert client.put(review_url, headers=workshop["attendee"], json={"decision": "approved"}).status_code == 403
    assert client.put(review_url, headers=faculty, json={"decision": "returned"}).status_code == 422
    feedback = {"decision": "returned", "comment": "Agrega el cálculo del término general.",
                "submitted_at": first["submitted_at"]}
    returned = client.put(review_url, headers=faculty, json=feedback)
    assert returned.status_code == 200, returned.text
    assert returned.json()["status"] == "returned"
    assert client.put(review_url, headers=faculty, json=feedback).json() == returned.json()

    updated = submit(client, workshop, "attendee", reflection="Agregué el cálculo.")
    assert updated.status_code == 201, updated.text
    second = updated.json()
    assert second["id"] == first["id"] and second["status"] == "submitted" and second["comment"] is None
    stale = client.put(review_url, headers=faculty, json={
        "decision": "approved", "submitted_at": first["submitted_at"],
    })
    assert stale.status_code == 409
    approved = client.put(review_url, headers=faculty, json={
        "decision": "approved", "submitted_at": second["submitted_at"],
    })
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
    assert submit(client, workshop, "attendee").status_code == 409
    assert client.put(review_url, headers=faculty, json=feedback).status_code == 409
