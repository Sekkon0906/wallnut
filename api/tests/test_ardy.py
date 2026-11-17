from test_evidence import record_attendance, workshop
from test_pilot import client
from test_wallet import allocation, approve, configure, evidence_path, faculty_context, upload


def test_ranking_counts_only_participation_and_respects_visibility(client, workshop):
    student = workshop["attendee"]
    faculty = workshop["faculty"]
    profile = "/v1/my-ardy"
    ranking = "/v1/participation-ranking"
    original = client.get(profile, headers=student).json()
    assert not original["show_in_ranking"]
    assert client.get(profile, headers=faculty).status_code == 403
    assert client.get(ranking).status_code == 401

    admin, faculty_id = faculty_context(client)
    allocation(client, admin, faculty_id, 80)
    configure(client, workshop)
    record_attendance(client, workshop)
    evidence = upload(client, workshop, "attendee")
    approve(client, workshop, evidence)
    assert client.get(ranking, headers=student).json() == {"entries": [], "me": None}

    avatar = {**original["avatar"], "fur": "gray", "texture": "curly", "height": 108}
    body = {"avatar": avatar, "show_in_ranking": True, "career": "Ingeniería de Sistemas"}
    assert client.put(profile, headers=student, json=body).json() == body
    assert client.get(profile, headers=student).json() == body
    assert client.put(profile, headers=student, json={**body, "avatar": {**avatar, "height": 120}}).status_code == 422

    initial = client.get(ranking, headers=student).json()["me"]
    assert initial["activities"] == 1
    assert initial["points"] > 0 and initial["position"] == 1 and initial["avatar"] == avatar
    path = evidence_path(workshop, evidence)
    assert client.post(f"{path}/goal", headers=faculty).is_success
    assert client.post(f"{path}/convert", headers=student).is_success
    assert client.get(ranking, headers=student).json()["me"] == initial

    assert client.put(profile, headers=student, json={**body, "show_in_ranking": False}).is_success
    assert client.get(ranking, headers=faculty).json() == {"entries": [], "me": None}
