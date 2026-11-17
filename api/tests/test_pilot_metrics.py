from uuid import uuid4

from test_pilot import client, sign_in
from test_workshops import open_workshop, workshop_team
from wallnut.database import connect


REPORT = "/v1/admin/pilot-metrics"


def test_only_admin_can_request_a_bounded_report(client, workshop_team):
    faculty, _, _, student, _ = workshop_team
    admin, _ = sign_in(client, "demo-admin")
    assert client.get(REPORT).status_code == 401
    for actor in (faculty, student):
        assert client.get(REPORT, headers=actor).status_code == 403
    for query in ("weeks=13", "weeks=0", "through=9999-12-31", "through=1900-01-01"):
        assert client.get(f"{REPORT}?{query}", headers=admin).status_code == 422

    result = client.get(f"{REPORT}?weeks=2&through=2025-02-10", headers=admin)
    assert result.is_success, result.text
    assert result.headers["cache-control"] == "private, no-store"
    report = result.json()
    assert report["time_zone"] == "America/Bogota"
    assert report["through"] == "2025-02-10"
    assert [week["week"] for week in report["weeks"]] == ["2025-02-10", "2025-02-03"]
    assert all(value == 0 for row in report["weeks"] for key, value in row.items() if key != "week")


def test_counts_linked_workshop_stages_and_weekly_operations_in_campus_time(client, workshop_team):
    faculty, course, facilitator, student, other = workshop_team
    admin, _ = sign_in(client, "demo-admin")
    _, maria = sign_in(client, "demo-student")
    _, mateo = sign_in(client, "demo-second-student")
    _, teacher = sign_in(client, "demo-faculty")
    completed = open_workshop(client, faculty, course, facilitator)
    cancelled = open_workshop(client, faculty, course, facilitator)
    in_progress = open_workshop(client, faculty, course, facilitator)
    for workshop in (completed, cancelled, in_progress):
        for participant in (student, other):
            assert client.put(f"/v1/workshops/{workshop}/enrollment", headers=participant).is_success

    event_id = uuid4()
    with connect() as db:
        db.execute("""
            UPDATE workshops SET starts_at = '2025-02-10 03:00+00', ends_at = '2025-02-10 04:00+00'
            WHERE id = ANY(%s::uuid[])
            """, ([completed, cancelled, in_progress],))
        db.execute("UPDATE workshops SET cancelled_at = '2025-02-10 02:00+00' WHERE id = %s", (cancelled,))
        db.execute("UPDATE workshops SET ends_at = '2025-02-11 06:00+00' WHERE id = %s", (in_progress,))
        db.execute("INSERT INTO workshop_attendance (workshop_id, student_id) VALUES (%s, %s)",
                   (completed, maria["id"]))
        result = db.execute("""
            INSERT INTO workshop_evidence (workshop_id, student_id, reflection, photo, photo_content_type,
                                           status, reviewed_by, reviewed_at)
            VALUES (%s, %s, 'Texto privado del taller.', %s, 'image/jpeg', 'approved', %s, now())
            RETURNING id
            """, (completed, maria["id"], b"example", teacher["id"])).fetchone()
        db.execute("""
            INSERT INTO wallet_movements (workshop_id, evidence_id, student_id, faculty_id, kind, points, coins, created_at)
            VALUES (%s, %s, %s, %s, 'evidence_reward', 3, 0, '2025-02-10 05:00+00')
            """, (completed, result["id"], maria["id"], teacher["id"]))
        db.execute("""
            INSERT INTO campus_events (id, organizer_id, institutional, title, description, category, location, starts_at, capacity)
            VALUES (%s, %s, false, 'Encuentro de prueba', 'Descripción privada', 'campus', 'Patio', '2025-02-10 14:00+00', 2)
            """, (event_id, maria["id"]))
        db.execute("INSERT INTO campus_event_enrollments (event_id, student_id) VALUES (%s, %s)", (event_id, mateo["id"]))
        db.execute("""
            INSERT INTO coin_payment_requests (id, recipient_id, payer_id, amount, paid_at)
            VALUES (%s, %s, %s, 2, '2025-02-10 12:00+00'), (%s, %s, NULL, 3, NULL)
            """, (uuid4(), mateo["id"], maria["id"], uuid4(), mateo["id"]))
        db.execute("""
            INSERT INTO ardy_nuts (id, student_id, item_id, price, taps, created_at)
            VALUES (%s, %s, 'rust_cap', 5, 3, '2025-02-10 14:00+00'),
                   (%s, %s, 'moon_cap', 5, 2, '2025-02-10 14:00+00'),
                   (%s, %s, 'sage_hoodie', 5, 3, '2025-02-11 05:00+00')
            """, (uuid4(), maria["id"], uuid4(), maria["id"], uuid4(), maria["id"]))

    result = client.get(f"{REPORT}?weeks=2&through=2025-02-10", headers=admin)
    assert result.is_success, result.text
    monday, earlier = result.json()["weeks"]
    assert monday["workshops"] == 0 and monday["points_awards"] == 1
    assert (monday["events"], monday["event_enrollments"], monday["coin_payments"]) == (1, 1, 1)
    assert (monday["nuts_purchased"], monday["nuts_opened"]) == (2, 1)
    assert earlier["workshops"] == 1 and earlier["workshop_enrollments"] == 2
    assert earlier["attendances"] == earlier["evidence_delivered"] == earlier["evidence_approved"] == 1
    assert earlier["points_awards"] == 0
    for private_value in (maria["id"], maria["email"], completed, "Texto privado", "Encuentro de prueba"):
        assert private_value not in result.text
