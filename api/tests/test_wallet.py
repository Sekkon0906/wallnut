from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from test_evidence import record_attendance, sample_photo, submit, workshop
from test_pilot import client, sign_in
from test_workshops import open_workshop


ECONOMY = {
    "attendee_points": 7,
    "facilitator_points": 9,
    "goal_description": "Justifica el criterio de convergencia que aplicaste.",
    "goal_coins": 8,
    "coin_cost": 5,
    "conversion_points": 6,
}


def faculty_context(client):
    admin, _ = sign_in(client, "demo-admin")
    _, faculty = sign_in(client, "demo-faculty")
    return admin, faculty["id"]


def allocation(client, admin, faculty_id, amount, request_id=None):
    return client.post(
        f"/v1/faculty-budgets/{faculty_id}/allocations", headers=admin,
        json={"points": amount, "request_id": request_id or str(uuid4())},
    )


def available(client, faculty, faculty_id):
    response = client.get("/v1/faculty-budgets", headers=faculty)
    assert response.status_code == 200, response.text
    rows = response.json()
    assert [row["faculty_id"] for row in rows] == [faculty_id]
    return rows[0]["available_points"]


def economy_path(workshop):
    return f"/v1/workshops/{workshop['id']}/economy"


def configure(client, workshop, **overrides):
    data = {**ECONOMY, **overrides}
    result = client.put(economy_path(workshop), headers=workshop["faculty"], json=data)
    assert result.is_success, result.text


def upload(client, workshop, role, photo=None):
    response = submit(client, workshop, role, photo=photo)
    assert response.status_code == 201, response.text
    return response.json()


def evidence_path(workshop, evidence):
    return f"{workshop['url']}/{evidence['id']}"


def approve(client, workshop, evidence):
    result = client.put(
        f"{evidence_path(workshop, evidence)}/review", headers=workshop["faculty"],
        json={"decision": "approved", "submitted_at": evidence["submitted_at"]},
    )
    assert result.status_code == 200, result.text
    approved = result.json()
    assert approved["status"] == "approved"
    return approved


def wallet(client, headers):
    response = client.get("/v1/wallet", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_approved_evidence_draws_from_the_faculty_budget_once(client, workshop):
    admin, faculty_id = faculty_context(client)
    assert client.get("/v1/faculty-budgets", headers=workshop["attendee"]).status_code == 403
    assert allocation(client, workshop["faculty"], faculty_id, 10).status_code == 403
    request_id = str(uuid4())
    first = allocation(client, admin, faculty_id, 10, request_id)
    assert first.is_success, first.text
    assert allocation(client, admin, faculty_id, 10, request_id).json() == first.json()
    assert allocation(client, admin, faculty_id, 11, request_id).status_code == 409
    assert available(client, workshop["faculty"], faculty_id) == 10

    partial_goal = client.put(
        economy_path(workshop), headers=workshop["faculty"],
        json={**ECONOMY, "goal_description": None},
    )
    assert partial_goal.status_code == 422
    configure(client, workshop)
    record_attendance(client, workshop)
    attendee = upload(client, workshop, "attendee")
    result = approve(client, workshop, attendee)
    assert result["points_awarded"] == 7
    assert approve(client, workshop, attendee)["points_awarded"] == 7
    assert available(client, workshop["faculty"], faculty_id) == 3
    movements = wallet(client, workshop["attendee"])["movements"]
    assert [(move["kind"], move["points"], move["coins"]) for move in movements] == [
        ("evidence_reward", 7, 0),
    ]
    locked = client.put(
        economy_path(workshop), headers=workshop["faculty"],
        json={**ECONOMY, "attendee_points": 8},
    )
    assert locked.status_code == 409

    facilitator = upload(client, workshop, "facilitator")
    assert approve(client, workshop, facilitator)["points_awarded"] == 0
    reward_url = f"{evidence_path(workshop, facilitator)}/reward"
    assert client.post(reward_url, headers=workshop["facilitator"]).status_code == 403
    assert client.post(reward_url, headers=workshop["faculty"]).status_code == 409
    assert allocation(client, admin, faculty_id, 9).is_success
    reward = client.post(reward_url, headers=workshop["faculty"])
    assert reward.is_success, reward.text
    assert client.post(reward_url, headers=workshop["faculty"]).is_success
    assert wallet(client, workshop["facilitator"])["points"] == 9
    assert available(client, workshop["faculty"], faculty_id) == 3


def test_verified_goal_and_conversion_are_idempotent_under_a_retry(client, workshop):
    admin, faculty_id = faculty_context(client)
    assert allocation(client, admin, faculty_id, 13).is_success
    configure(client, workshop)
    record_attendance(client, workshop)
    record = upload(client, workshop, "attendee")
    path = evidence_path(workshop, record)
    faculty, student = workshop["faculty"], workshop["attendee"]
    assert client.post(f"{path}/goal", headers=faculty).status_code == 409
    approve(client, workshop, record)
    assert client.post(f"{path}/convert", headers=student).status_code == 409
    assert client.post(f"{path}/goal", headers=student).status_code == 403
    assert client.post(f"{path}/goal", headers=faculty).is_success
    assert client.post(f"{path}/goal", headers=faculty).is_success
    other_attempt = client.post(f"{path}/convert", headers=workshop["facilitator"])
    assert other_attempt.status_code in (403, 404)
    assert client.get(workshop["url"], headers=student).json()[0]["goal_verified"]
    state = wallet(client, student)
    assert (state["coins"], state["points"]) == (8, 7)
    opportunity = state["conversions"][0]
    assert opportunity["evidence_id"] == record["id"]
    assert opportunity["coin_cost"] == 5 and opportunity["points"] == 6
    assert opportunity["goal"] == ECONOMY["goal_description"]
    assert not opportunity["converted"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(
            lambda _: client.post(f"{path}/convert", headers=student), range(2),
        ))
    assert all(result.is_success for result in results), [result.text for result in results]
    assert results[0].json()["id"] == results[1].json()["id"]
    state = wallet(client, student)
    assert (state["coins"], state["points"]) == (3, 13)
    assert state["conversions"][0]["converted"]
    conversion = next(move for move in state["movements"] if move["kind"] == "coin_conversion")
    assert (conversion["coins"], conversion["points"], conversion["course"]) == (-5, 6, "Cálculo III")
    assert [move["kind"] for move in state["movements"]].count("coin_conversion") == 1
    assert available(client, faculty, faculty_id) == 0


def test_concurrent_conversions_cannot_overspend_quota_or_lose_coins(client, workshop):
    admin, faculty_id = faculty_context(client)
    assert allocation(client, admin, faculty_id, 6).is_success
    configure(client, workshop, attendee_points=0, facilitator_points=0)
    record_attendance(client, workshop)
    faculty = workshop["faculty"]
    photo = sample_photo()
    attempts = []
    for role in ("attendee", "facilitator"):
        record = upload(client, workshop, role, photo=photo)
        assert approve(client, workshop, record)["points_awarded"] == 0
        path = evidence_path(workshop, record)
        assert client.post(f"{path}/goal", headers=faculty).is_success
        attempts.append((f"{path}/convert", workshop[role]))

    def make_conversion(attempt):
        path, headers = attempt
        return client.post(path, headers=headers)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(make_conversion, attempts))
    assert sum(result.is_success for result in results) == 1
    failed = next(index for index, result in enumerate(results) if not result.is_success)
    assert results[failed].status_code == 409, results[failed].text
    for index, (_, headers) in enumerate(attempts):
        state = wallet(client, headers)
        expected = (8, 0) if index == failed else (3, 6)
        assert (state["coins"], state["points"]) == expected
    assert available(client, faculty, faculty_id) == 0


def test_same_student_cannot_spend_the_same_coins_in_two_workshops(client, workshop):
    admin, faculty_id = faculty_context(client)
    assert allocation(client, admin, faculty_id, 12).is_success
    faculty, student = workshop["faculty"], workshop["attendee"]
    courses = client.get("/v1/courses", headers=faculty)
    assert courses.is_success, courses.text
    other_id = open_workshop(client, faculty, courses.json()[0]["id"], workshop["facilitator"])
    other = {**workshop, "id": other_id, "url": f"/v1/workshops/{other_id}/evidence"}
    assert client.put(f"/v1/workshops/{other_id}/enrollment", headers=student).status_code == 201

    photo = sample_photo()
    paths = []
    for item in (workshop, other):
        configure(client, item, attendee_points=0, facilitator_points=0, goal_coins=4, coin_cost=8)
        record_attendance(client, item)
        record = upload(client, item, "attendee", photo=photo)
        approve(client, item, record)
        path = evidence_path(item, record)
        assert client.post(f"{path}/goal", headers=faculty).is_success
        paths.append(f"{path}/convert")
    assert wallet(client, student)["coins"] == 8

    with ThreadPoolExecutor(max_workers=2) as executor:
        attempts = list(executor.map(lambda path: client.post(path, headers=student), paths))
    assert sum(attempt.is_success for attempt in attempts) == 1
    denied = next(attempt for attempt in attempts if not attempt.is_success)
    assert denied.status_code == 409, denied.text
    state = wallet(client, student)
    assert (state["coins"], state["points"]) == (0, 6)
    assert len([move for move in state["movements"] if move["kind"] == "coin_conversion"]) == 1
    assert available(client, faculty, faculty_id) == 6
