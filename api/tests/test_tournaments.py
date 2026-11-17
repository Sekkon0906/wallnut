from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from test_pilot import client, setup_campus, sign_in
from wallnut.tournaments import seeded_matches


def open_tournament(client, organizer):
    event = client.post("/v1/campus-events", headers=organizer, json={
        "id": str(uuid4()),
        "title": "Torneo de pádel",
        "description": "Inscripción para el torneo individual.",
        "category": "tournament",
        "location": "Canchas",
        "capacity": 8,
        "starts_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    })
    assert event.status_code == 201, event.text
    assert event.json()["registration_open"]
    return f"/v1/campus-events/{event.json()['id']}"


def test_bracket_closes_registration_and_advances_the_winner(client):
    admin, organizer, _ = setup_campus(client)
    first, a = sign_in(client, "demo-student")
    second, b = sign_in(client, "demo-second-student")
    verifier = client.app.state.verify_identity
    client.app.state.verify_identity = lambda credential: (
        {**verifier("demo-student"), "sub": "third-student", "name": "Tercera estudiante",
         "email": "tercera@estudiantesunibague.edu.co"}
        if credential == "third-student" else verifier(credential)
    )
    third, c = sign_in(client, "third-student")

    event = open_tournament(client, organizer)
    url = f"{event}/tournament"
    publish = f"{url}/bracket"
    enrollment = f"{event}/enrollment"
    assert client.get(url).status_code == 401
    assert client.post(publish, headers=first).status_code == 403
    assert client.post(publish, headers=organizer).status_code == 409
    for student in (first, second, third):
        assert client.put(enrollment, headers=student).status_code == 200

    registration = client.get(url, headers=organizer).json()
    assert registration["state"] == "registration" and registration["can_generate"]
    assert not client.get(url, headers=third).json()["can_manage"]
    published = client.post(publish, headers=organizer)
    assert published.status_code == 200, published.text
    bracket = published.json()
    assert bracket["state"] == "in_progress"
    assert bracket["participant_count"] == 3
    assert client.post(publish, headers=organizer).json() == bracket
    assert client.delete(enrollment, headers=first).status_code == 409
    listed = client.get("/v1/campus-events", headers=first).json()[0]
    assert listed["upcoming"] and not listed["registration_open"]

    opening, final = [item["matches"] for item in bracket["rounds"]]
    bye, = [game for game in opening if game["status"] == "bye"]
    playable, = [game for game in opening if game["status"] == "ready"]
    assert {bye["first"]["id"], playable["first"]["id"], playable["second"]["id"]} == {
        a["id"], b["id"], c["id"],
    }
    assert final[0]["status"] == "waiting"
    assert bye["winner_id"] in {entry["id"] for entry in (final[0]["first"], final[0]["second"]) if entry}
    match = f"{url}/matches/1/{playable['number']}"
    winner = playable["first"]["id"]
    assert client.put(match, headers=first, json={"winner_id": winner}).status_code == 403
    assert client.put(match, headers=organizer, json={"winner_id": bye["winner_id"]}).status_code == 422
    assert client.put(match, headers=organizer, json={"winner_id": winner, "score": "6\x00–4"}).status_code == 422
    assert client.put(f"{url}/matches/2/1", headers=organizer, json={"winner_id": winner}).status_code == 409

    body = {"winner_id": winner, "score": " 6–3, 6–4 "}
    advanced = client.put(match, headers=organizer, json=body)
    assert advanced.status_code == 200, advanced.text
    state = advanced.json()
    assert client.put(match, headers=organizer, json=body).json() == state
    assert client.put(match, headers=organizer, json={"winner_id": winner, "score": "6–0"}).status_code == 409
    assert state["rounds"][0]["matches"][playable["number"] - 1]["score"] == "6–3, 6–4"
    final = state["rounds"][1]["matches"][0]
    assert final["status"] == "ready"
    assert {final["first"]["id"], final["second"]["id"]} == {winner, bye["winner_id"]}
    complete = client.put(f"{url}/matches/2/1", headers=organizer, json={"winner_id": winner}).json()
    assert complete["state"] == "completed"
    assert complete["champion"] == playable["first"]

    assert client.put(f"{event}/cancel", headers=admin).json()["cancelled"]
    assert client.get(url, headers=first).json()["state"] == "cancelled"
    assert client.post(publish, headers=organizer).status_code == 409


def test_parallel_conflicting_results_only_advance_one_winner(client):
    _, organizer, _ = setup_campus(client)
    first, _ = sign_in(client, "demo-student")
    second, _ = sign_in(client, "demo-second-student")
    event = open_tournament(client, organizer)
    for student in (first, second):
        assert client.put(f"{event}/enrollment", headers=student).status_code == 200
    url = f"{event}/tournament"
    bracket = client.post(f"{url}/bracket", headers=organizer).json()
    game = bracket["rounds"][0]["matches"][0]

    def record(entrant):
        return client.put(f"{url}/matches/1/1", headers=organizer, json={"winner_id": entrant["id"]})

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(record, (game["first"], game["second"])))
    assert sorted(result.status_code for result in results) == [200, 409]
    champion = next(result.json()["champion"] for result in results if result.status_code == 200)
    assert client.get(url, headers=first).json()["champion"] == champion


@pytest.mark.parametrize("count", [2, 3, 5, 8, 9, 500])
def test_bracket_places_every_entrant_once_and_propagates_byes(count):
    entrants = list(range(1, count + 1))
    rounds = seeded_matches(entrants)
    assert sorted(slot for first, second, _ in rounds[0] for slot in (first, second) if slot) == entrants
    assert sum(len(group) for group in rounds) == len(rounds[0]) * 2 - 1
    for index, (first, second, winner) in enumerate(rounds[0]):
        if second is None:
            assert winner == first == rounds[1][index // 2][index % 2]
        else:
            assert winner is None
