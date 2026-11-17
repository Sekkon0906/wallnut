from datetime import datetime, timedelta, timezone
from uuid import uuid4

from test_pilot import client, sign_in


def test_campus_profile_visibility_controls_both_events_and_direct_access(client):
    student, maria = sign_in(client, "demo-student")
    viewer, _ = sign_in(client, "demo-second-student")
    staff, _ = sign_in(client, "external-staff")
    settings = "/v1/my-campus-profile"
    profile = f"/v1/campus-profiles/{maria['id']}"
    events = "/v1/campus-events"

    assert client.get(settings, headers=student).json() == {"bio": "", "visible": False, "show_career": False}
    assert client.put(settings, headers=staff, json={"visible": True}).status_code == 403
    assert client.get(profile, headers=viewer).status_code == 404
    assert client.get(profile).status_code == 401

    ardy = client.get("/v1/my-ardy", headers=student).json()
    ardy["career"] = "Ingeniería de Sistemas"
    ardy["avatar"]["fur"] = "gray"
    assert client.put("/v1/my-ardy", headers=student, json=ardy).is_success
    event = client.post(events, headers=student, json={
        "id": str(uuid4()),
        "title": "Taller de programación",
        "description": "Repaso de estructuras de datos.",
        "category": "workshop",
        "location": "Biblioteca",
        "capacity": 10,
        "starts_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    })
    assert event.status_code == 201, event.text
    assert not event.json()["organizer_profile_visible"]
    assert client.put(settings, headers=student, json={"bio": "x" * 281}).status_code == 422

    visible = {"visible": True, "show_career": False, "bio": "Me gusta enseñar programación."}
    assert client.put(settings, headers=student, json=visible).json() == visible
    assert client.get(events, headers=viewer).json()[0]["organizer_profile_visible"]
    response = client.get(profile, headers=viewer)
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json() == {
        "display_name": maria["display_name"], "career": None, "bio": visible["bio"], "avatar": ardy["avatar"],
    }

    assert client.put(settings, headers=student, json={**visible, "show_career": True}).is_success
    assert client.get(profile, headers=viewer).json()["career"] == ardy["career"]
    assert client.put(settings, headers=student, json={**visible, "visible": False}).is_success
    assert not client.get(events, headers=viewer).json()[0]["organizer_profile_visible"]
    assert client.get(profile, headers=viewer).status_code == 404
