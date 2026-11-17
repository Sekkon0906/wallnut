from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from test_pilot import client, setup_campus, sign_in


def doubles_input(**changes):
    return {
        "id": str(uuid4()), "category": "tournament", "title": "Pádel por parejas",
        "description": "Torneo del campus con parejas inscritas.", "location": "Cancha",
        "starts_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "capacity": 8, "tournament_format": "doubles", **changes,
    }


def participant_accounts(client):
    return [sign_in(client, credential) for credential in (
        "demo-student", "demo-second-student", "demo-third-student", "demo-fourth-student",
    )]


def setup_doubles(client, organizer, participants):
    event = client.post("/v1/campus-events", headers=organizer, json=doubles_input())
    assert event.status_code == 201, event.text
    event_url = f"/v1/campus-events/{event.json()['id']}"
    for headers, _ in participants:
        assert client.put(f"{event_url}/enrollment", headers=headers).status_code == 200
    return event_url, f"{event_url}/tournament"


def send_invitation(client, url, headers, other):
    body = {"student_id": other["id"], "id": str(uuid4())}
    result = client.post(f"{url}/pair-invitations", headers=headers, json=body)
    assert result.status_code == 201, result.text
    return f"{url}/pair-invitations/{body['id']}", body


def test_confirmed_pairs_are_seeded_and_win_together(client):
    _, organizer, _ = setup_campus(client)
    members = participant_accounts(client)
    (first, maria), (second, mateo), (third, camila), (fourth, julian) = members
    verifier = client.app.state.verify_identity
    client.app.state.verify_identity = lambda credential: (
        {**verifier("demo-student"), "sub": "one-more-student", "name": "Quinto Piloto",
         "email": "quinto@estudiantesunibague.edu.co"}
        if credential == "one-more-student" else verifier(credential)
    )
    extra, _ = sign_in(client, "one-more-student")
    for invalid in (doubles_input(capacity=3), doubles_input(capacity=5), doubles_input(category="campus")):
        assert client.post("/v1/campus-events", headers=organizer, json=invalid).status_code == 422

    event, url = setup_doubles(client, organizer, members)
    private = client.get(f"{url}/pairing", headers=extra)
    assert private.headers["cache-control"] == "private, no-store"
    assert private.json() == {"open": True, "enrolled": False, "pair": None, "invitations": [], "available": []}
    assert client.get(f"{url}/pairing", headers=organizer).status_code == 403
    assert client.get(f"{url}/pairing").status_code == 401
    assert client.put(f"{event}/enrollment", headers=extra).status_code == 200

    first_invite, body = send_invitation(client, url, first, mateo)
    assert client.post(f"{url}/pair-invitations", headers=first, json=body).status_code == 201
    assert client.get(f"{url}/pairing", headers=third).json()["invitations"] == []
    assert client.put(f"{first_invite}/accept", headers=first).status_code == 404
    accepted = client.put(f"{first_invite}/accept", headers=second)
    assert accepted.is_success, accepted.text
    assert accepted.json()["pair"]["name"] == maria["display_name"]
    assert client.put(f"{first_invite}/accept", headers=second).json() == accepted.json()

    waiting = client.get(url, headers=organizer).json()
    assert waiting["tournament_format"] == "doubles"
    assert waiting["entrant_count"] == 1 and waiting["unpaired_count"] == 3
    assert client.post(f"{url}/bracket", headers=organizer).status_code == 409
    second_invite, _ = send_invitation(client, url, third, julian)
    assert client.put(f"{second_invite}/accept", headers=fourth).is_success

    published = client.post(f"{url}/bracket", headers=organizer)
    assert published.is_success, published.text
    bracket = published.json()
    assert bracket["entrant_count"] == 2 and bracket["unpaired_count"] == 1
    assert not client.get(f"{url}/pairing", headers=first).json()["open"]
    assert client.delete(first_invite, headers=second).status_code == 409
    assert client.delete(f"{event}/enrollment", headers=second).status_code == 409
    game = bracket["rounds"][0]["matches"][0]
    assert {game["first"]["name"], game["second"]["name"]} == {
        "María Piloto y Mateo Piloto", "Camila Piloto y Julián Piloto",
    }
    result = client.put(f"{url}/matches/1/1", headers=organizer, json={"winner_id": game["first"]["id"]})
    assert result.is_success, result.text
    assert result.json()["champion"] == game["first"]


def test_accepting_concurrent_invitations_creates_only_one_pair(client):
    _, organizer, _ = setup_campus(client)
    members = participant_accounts(client)
    (first, _), (second, mateo), (third, _), _ = members
    event, url = setup_doubles(client, organizer, members)
    first_invite, _ = send_invitation(client, url, first, mateo)
    other_invite, _ = send_invitation(client, url, third, mateo)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda path: client.put(f"{path}/accept", headers=second), (first_invite, other_invite)))
    assert sorted(item.status_code for item in results) == [200, 404]
    pairing = client.get(f"{url}/pairing", headers=second).json()
    assert pairing["pair"] and pairing["invitations"] == []
    assert client.get(url, headers=organizer).json()["entrant_count"] == 1

    assert client.delete(f"{event}/enrollment", headers=second).status_code == 200
    assert client.get(url, headers=organizer).json()["entrant_count"] == 0
    for headers in (first, third):
        assert client.get(f"{url}/pairing", headers=headers).json()["pair"] is None
    assert client.put(f"{other_invite}/accept", headers=second).status_code == 404
