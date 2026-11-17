from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from test_evidence import record_attendance, sample_photo, workshop
from test_pilot import client, sign_in
from test_wallet import allocation, approve, configure, faculty_context, upload, wallet
from test_workshops import open_workshop
from wallnut.database import connect


def checked(response):
    assert response.is_success, response.text
    return response.json()


def grade_path(course_id):
    return f"/v1/courses/{course_id}/grade-redemption"


def source_group(client, faculty):
    return checked(client.get("/v1/courses", headers=faculty))[0]["id"]


def add_group(client, admin, faculty_id, code):
    response = client.post("/v1/courses", headers=admin, json={
        "code": code, "title": f"Grupo {code}", "term": "PILOTO",
        "section": "01", "faculty_id": faculty_id,
    })
    return checked(response)["id"]


def confirm_enrollment(client, faculty, course_id, student_email):
    return checked(client.put(f"/v1/courses/{course_id}/students", headers=faculty,
                              json={"email": student_email}))


def rule(sources, **overrides):
    return {
        "assessment": "Primer corte", "points_per_step": 4, "step_milli": 30,
        "max_bonus_milli": 75, "minimum_grade_milli": 3500,
        "accepted_course_ids": sources, **overrides,
    }


def configure_rule(client, faculty, target, data):
    return client.put(f"{grade_path(target)}/rule", headers=faculty, json=data)


def simulate_grade(client, faculty, target, student_id, grade):
    return client.put(
        f"{grade_path(target)}/students/{student_id}", headers=faculty,
        json={"base_grade_milli": grade},
    )


def redemption(client, student, target, steps, request_id=None):
    return client.post(f"{grade_path(target)}/requests", headers=student, json={
        "steps": steps, "request_id": request_id or str(uuid4()),
    })


def review(client, faculty, target, redemption_id, decision, reason=None):
    return client.put(
        f"{grade_path(target)}/requests/{redemption_id}/review", headers=faculty,
        json={"decision": decision, "reason": reason},
    )


def earn_from_workshop(client, instance, points, scope):
    configure(client, instance, attendee_points=points, points_scope=scope)
    record_attendance(client, instance)
    evidence = upload(client, instance, "attendee", photo=sample_photo())
    approved = approve(client, instance, evidence)
    assert approved["points_awarded"] == points


def another_workshop(client, first, course_id):
    identity = open_workshop(client, first["faculty"], course_id, first["facilitator"])
    assert client.put(
        f"/v1/workshops/{identity}/enrollment", headers=first["attendee"],
    ).status_code == 201
    return {**first, "id": identity, "url": f"/v1/workshops/{identity}/evidence"}


def configure_course(client, workshop, target, data, grade=3800):
    faculty = workshop["faculty"]
    _, student = sign_in(client, "demo-student")
    confirm_enrollment(client, faculty, target, student["email"])
    assert configure_rule(client, faculty, target, data).is_success
    assert simulate_grade(client, faculty, target, student["id"], grade).is_success


def test_origin_policy_and_simulated_grade_limits(client, workshop):
    admin, faculty_id = faculty_context(client)
    faculty, student = workshop["faculty"], workshop["attendee"]
    source = source_group(client, faculty)
    other = add_group(client, admin, faculty_id, "MAT304")
    _, other_faculty = sign_in(client, "external-staff")
    assert client.post("/v1/faculty", headers=admin, json={"email": other_faculty["email"]}).is_success
    assert {row["id"] for row in checked(client.get("/v1/grade-redemptions/courses", headers=faculty))} == {source, other}
    assert client.get("/v1/grade-redemptions/courses", headers=student).status_code == 403

    assert allocation(client, admin, faculty_id, 28).is_success
    earn_from_workshop(client, workshop, 14, "course_only")
    portable = another_workshop(client, workshop, source)
    earn_from_workshop(client, portable, 14, "accepted_courses")

    assert client.get(grade_path(other), headers=student).status_code in (403, 404)
    assert simulate_grade(client, faculty, other, workshop["student_id"], 3400).status_code in (403, 404, 409)
    assert configure_rule(client, workshop["unauthorized"], other, rule([source])).status_code in (403, 404)
    configure_course(client, workshop, other, rule([other]), grade=3400)
    receiving = checked(client.get(grade_path(other), headers=student))
    assert receiving["student"]["eligible_points"] == 0
    assert receiving["roster"] == []

    assert configure_rule(client, faculty, other, rule([source])).is_success
    receiving = checked(client.get(grade_path(other), headers=student))
    assert receiving["student"]["eligible_points"] == 14
    assert redemption(client, student, other, 1).status_code == 409

    assert simulate_grade(client, faculty, other, workshop["student_id"], 4990).is_success
    assert redemption(client, student, other, 1).status_code == 409
    assert simulate_grade(client, faculty, other, workshop["student_id"], 3800).is_success
    assert redemption(client, student, other, 3).status_code == 409
    pending = checked(redemption(client, student, other, 2))
    assert (pending["points"], pending["boost_milli"]) == (8, 60)
    assert (pending["grade_before_milli"], pending["grade_after_milli"]) == (3800, 3860)
    assert review(client, workshop["unauthorized"], other, pending["id"], "approved").status_code in (403, 404)
    assert review(client, faculty, other, pending["id"], "approved").is_success
    simulation = checked(client.get(grade_path(other), headers=student))["student"]
    assert simulation["simulated_grade_milli"] == 3860
    assert simulation["eligible_points"] == 6
    assert simulation["remaining_bonus_milli"] == 15
    assert redemption(client, student, other, 1).status_code == 409


def test_redemption_reserves_releases_and_records_points_once(client, workshop):
    admin, faculty_id = faculty_context(client)
    faculty, student = workshop["faculty"], workshop["attendee"]
    course = source_group(client, faculty)
    assert allocation(client, admin, faculty_id, 20).is_success
    earn_from_workshop(client, workshop, 20, "course_only")
    configure_course(client, workshop, course, rule([course]))

    request_id = str(uuid4())
    first = checked(redemption(client, student, course, 2, request_id))
    assert first["status"] == "pending"
    assert checked(redemption(client, student, course, 2, request_id))["id"] == first["id"]
    assert redemption(client, student, course, 1, request_id).status_code == 409
    assert redemption(client, student, course, 1).status_code == 409
    reserved = wallet(client, student)
    assert (reserved["points"], reserved["reserved_points"]) == (12, 8)
    assert all(move["kind"] != "grade_redemption" for move in reserved["movements"])
    assert simulate_grade(client, faculty, course, workshop["student_id"], 3900).status_code == 409

    assert review(client, faculty, course, first["id"], "rejected").status_code == 422
    rejected = checked(review(client, faculty, course, first["id"], "rejected", "Revisar la nota base simulada."))
    assert rejected["status"] == "rejected"
    assert rejected["reason"] == "Revisar la nota base simulada."
    restored = wallet(client, student)
    assert (restored["points"], restored["reserved_points"]) == (20, 0)

    second = checked(redemption(client, student, course, 2))
    approved = checked(review(client, faculty, course, second["id"], "approved"))
    assert approved["status"] == "approved"
    assert checked(review(client, faculty, course, second["id"], "approved"))["id"] == second["id"]
    assert review(client, faculty, course, second["id"], "rejected", "No se debe revertir.").status_code == 409
    final = wallet(client, student)
    assert (final["points"], final["reserved_points"]) == (12, 0)
    deductions = [move for move in final["movements"] if move["kind"] == "grade_redemption"]
    assert [(move["points"], move["coins"], move["course"]) for move in deductions] == [(-8, 0, "Cálculo III")]


def test_two_courses_cannot_reserve_the_same_points_concurrently(client, workshop):
    admin, faculty_id = faculty_context(client)
    faculty, student = workshop["faculty"], workshop["attendee"]
    source = source_group(client, faculty)
    targets = [
        add_group(client, admin, faculty_id, "MAT304"),
        add_group(client, admin, faculty_id, "MAT305"),
    ]
    assert allocation(client, admin, faculty_id, 10).is_success
    earn_from_workshop(client, workshop, 4, "accepted_courses")
    earn_from_workshop(client, another_workshop(client, workshop, source), 6, "accepted_courses")
    for target in targets:
        configure_course(client, workshop, target, rule([source], points_per_step=6))

    with ThreadPoolExecutor(max_workers=2) as executor:
        attempts = list(executor.map(lambda target: redemption(client, student, target, 1), targets))
    assert sum(attempt.is_success for attempt in attempts) == 1
    denied = next(attempt for attempt in attempts if not attempt.is_success)
    assert denied.status_code == 409, denied.text
    result = wallet(client, student)
    assert (result["points"], result["reserved_points"]) == (4, 6)


def test_teachers_can_set_rules_with_each_others_course_as_an_origin(client, workshop):
    admin, _ = faculty_context(client)
    first_teacher = workshop["faculty"]
    second_teacher, second_account = sign_in(client, "external-staff")
    assert client.post("/v1/faculty", headers=admin, json={"email": second_account["email"]}).is_success
    first = source_group(client, first_teacher)
    second = add_group(client, admin, second_account["id"], "MAT304")

    # Both requests hold their course lock before either source foreign key is checked.
    with connect() as db:
        db.execute("""
            CREATE SEQUENCE rule_source_test_barrier;
            CREATE FUNCTION await_other_source_insert() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                PERFORM nextval('rule_source_test_barrier');
                FOR sample IN 1..500 LOOP
                    IF (SELECT last_value FROM rule_source_test_barrier) >= 2 THEN
                        RETURN NEW;
                    END IF;
                    PERFORM pg_sleep(0.01);
                END LOOP;
                RAISE EXCEPTION 'Timed out waiting for the other course to insert its source';
            END;
            $$;
            CREATE TRIGGER synchronize_source_fk_checks
                BEFORE INSERT ON grade_redemption_sources
                FOR EACH ROW EXECUTE FUNCTION await_other_source_insert();
        """)

    def save_rule(change):
        teacher, target, source = change
        return configure_rule(client, teacher, target, rule([source]))

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(save_rule, [
            (first_teacher, first, second),
            (second_teacher, second, first),
        ]))
    assert [checked(result)["accepted_course_ids"] for result in results] == [[second], [first]]
