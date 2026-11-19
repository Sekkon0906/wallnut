from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, StringConstraints, model_validator

from .database import Database
from .economy import PositiveAmount, lock_student_wallet
from .identity import CurrentAccount
from .notifications import record_notification

router = APIRouter(tags=["Nota simulada"])
MAX_GRADE = 5000
Grade = Annotated[int, Field(strict=True, ge=0, le=MAX_GRADE)]
Boost = Annotated[int, Field(strict=True, ge=1, le=MAX_GRADE)]
Assessment = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
RULE_COLUMNS = "assessment, points_per_step, step_milli, max_bonus_milli, minimum_grade_milli"
REQUESTS = """
    SELECT r.id, r.student_id, a.display_name, r.assessment, r.points, r.boost_milli, r.grade_before_milli,
           r.grade_after_milli, r.status, r.reason, r.created_at
    FROM grade_redemptions r JOIN accounts a ON a.id = r.student_id
"""


class GradeRule(BaseModel):
    assessment: Assessment
    points_per_step: PositiveAmount
    step_milli: Boost
    max_bonus_milli: Boost
    minimum_grade_milli: Grade | None = None
    accepted_course_ids: Annotated[list[UUID], Field(min_length=1, max_length=100)]

    @model_validator(mode="after")
    def validate_config(self):
        if self.max_bonus_milli < self.step_milli:
            raise ValueError("El tope debe permitir al menos un incremento.")
        if len(set(self.accepted_course_ids)) != len(self.accepted_course_ids):
            raise ValueError("Cada grupo de origen se selecciona una sola vez.")
        return self


class SimulatedGrade(BaseModel):
    base_grade_milli: Grade


class RedemptionInput(BaseModel):
    steps: Annotated[int, Field(strict=True, ge=1, le=MAX_GRADE)]
    request_id: UUID


class RedemptionReview(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: Reason | None = None


def require_faculty(account):
    if account.role != "faculty":
        raise HTTPException(403, "Esta acción requiere una cuenta docente.")


def course_access(db, course_id, account, *, lock="", faculty_only=False):
    if faculty_only:
        require_faculty(account)
    row = db.execute(
        f"""
        SELECT s.faculty_id,
               EXISTS (SELECT 1 FROM enrollments e WHERE e.course_id = s.id
                       AND e.account_id = %(account)s) AS enrolled
        FROM course_sections s WHERE s.id = %(course)s {lock}
        """,
        {"course": course_id, "account": account.id},
    ).fetchone()
    if not row:
        raise HTTPException(404, "No encontramos el grupo.")
    is_owner = account.role == "faculty" and row["faculty_id"] == account.id
    if not is_owner and (faculty_only or account.role != "student" or not row["enrolled"]):
        raise HTTPException(403, "El canje académico requiere matrícula confirmada o el docente asignado.")
    return is_owner


def has_active_redemptions(db, course_id, student_id=None):
    where = "WHERE course_id = %s AND status IN ('pending', 'approved')"
    params = [course_id]
    if student_id is not None:
        where += " AND student_id = %s"
        params.append(student_id)
    return db.execute("SELECT 1 FROM grade_redemptions " + where + " LIMIT 1", params).fetchone() is not None


def get_rule(db, course_id):
    return db.execute(
        f"""
        SELECT {RULE_COLUMNS}, ARRAY(
            SELECT source_course_id FROM grade_redemption_sources
            WHERE course_id = %(course)s ORDER BY source_course_id
        ) AS accepted_course_ids
        FROM grade_redemption_rules WHERE course_id = %(course)s
        """,
        {"course": course_id},
    ).fetchone()


def eligible_lots(db, student_id, target_id):
    return db.execute(
        """
        SELECT m.id, m.points - coalesce(used.points, 0) AS available
        FROM wallet_movements m
        JOIN workshops w ON w.id = m.workshop_id
        JOIN workshop_calls c ON c.id = w.call_id
        JOIN workshop_economies p ON p.workshop_id = w.id
        JOIN grade_redemption_sources src ON src.course_id = %(target)s AND src.source_course_id = c.course_id
        LEFT JOIN LATERAL (
            SELECT sum(d.points) AS points
            FROM grade_redemption_debits d JOIN grade_redemptions r ON r.id = d.redemption_id
            WHERE d.movement_id = m.id AND r.status IN ('pending', 'approved')
        ) used ON true
        WHERE m.student_id = %(student)s AND m.points > coalesce(used.points, 0)
          AND (p.points_scope = 'accepted_courses' OR c.course_id = %(target)s)
        ORDER BY m.created_at, m.id
        """,
        {"student": student_id, "target": target_id},
    ).fetchall()


def grade_progress(db, course_id, student_id):
    return db.execute(
        """
        SELECT g.base_grade_milli AS base_grade_milli,
               g.base_grade_milli + coalesce(sum(r.boost_milli) FILTER (WHERE r.status = 'approved'), 0)
                   AS simulated_grade_milli,
               coalesce(sum(r.boost_milli) FILTER (WHERE r.status IN ('pending', 'approved')), 0)
                   AS used_bonus_milli,
               coalesce(bool_or(r.status = 'pending'), false) AS has_pending
        FROM simulated_grades g
        LEFT JOIN grade_redemptions r ON r.course_id = g.course_id AND r.student_id = g.student_id
        WHERE g.course_id = %s AND g.student_id = %s
        GROUP BY g.base_grade_milli
        """,
        (course_id, student_id),
    ).fetchone()


def bonus_remaining(policy, grade):
    if not policy:
        return 0
    limit = min(policy["max_bonus_milli"], MAX_GRADE - grade["base_grade_milli"])
    return max(limit - grade["used_bonus_milli"], 0)


def request_detail(db, redemption_id):
    return db.execute(REQUESTS + " WHERE r.id = %s", (redemption_id,)).fetchone()


@router.get("/grade-redemptions/courses")
def course_catalog(account: CurrentAccount, db: Database):
    require_faculty(account)
    return db.execute(
        "SELECT id, code, title, term, section FROM course_sections ORDER BY term DESC, title, code, section"
    ).fetchall()


@router.get("/courses/{course_id}/grade-redemption")
def read_redemptions(course_id: UUID, account: CurrentAccount, db: Database, response: Response):
    with db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        faculty = course_access(db, course_id, account)
        rule = get_rule(db, course_id)
        if rule:
            rule["locked"] = has_active_redemptions(db, course_id)

        student = None
        roster = []
        where = "WHERE r.course_id = %s"
        params = [course_id]
        if faculty:
            roster = db.execute(
                """
                SELECT a.id AS student_id, a.display_name, a.email, g.base_grade_milli,
                       EXISTS (SELECT 1 FROM grade_redemptions r WHERE r.course_id = e.course_id
                               AND r.student_id = e.account_id AND r.status IN ('pending', 'approved')) AS locked
                FROM enrollments e JOIN accounts a ON a.id = e.account_id
                LEFT JOIN simulated_grades g ON g.course_id = e.course_id AND g.student_id = e.account_id
                WHERE e.course_id = %s ORDER BY a.display_name, a.id
                """,
                (course_id,),
            ).fetchall()
        else:
            where += " AND r.student_id = %s"
            params.append(account.id)
            progress = grade_progress(db, course_id, account.id)
            if progress:
                student = {
                    "base_grade_milli": progress["base_grade_milli"],
                    "simulated_grade_milli": progress["simulated_grade_milli"],
                    "eligible_points": sum(lot["available"] for lot in eligible_lots(db, account.id, course_id)),
                    "remaining_bonus_milli": bonus_remaining(rule, progress),
                }
        requests = db.execute(
            REQUESTS + where + " ORDER BY (r.status = 'pending') DESC, r.created_at DESC, r.id DESC",
            params,
        ).fetchall()
    response.headers["Cache-Control"] = "private, no-store"
    return {"rule": rule, "roster": roster, "requests": requests, "student": student}


@router.put("/courses/{course_id}/grade-redemption/rule")
def set_rule(course_id: UUID, body: GradeRule, account: CurrentAccount, db: Database):
    with db.transaction():
        course_access(db, course_id, account, lock="FOR NO KEY UPDATE OF s", faculty_only=True)
        previous = get_rule(db, course_id)
        settings = {**body.model_dump(), "accepted_course_ids": sorted(body.accepted_course_ids)}
        locked = has_active_redemptions(db, course_id)
        if previous == settings:
            return {**previous, "locked": locked}
        if locked:
            raise HTTPException(409, "La regla se conserva mientras existan solicitudes pendientes o aprobadas.")
        known = db.execute(
            "SELECT count(*) AS total FROM course_sections WHERE id = ANY(%s)",
            (body.accepted_course_ids,),
        ).fetchone()["total"]
        if known != len(body.accepted_course_ids):
            raise HTTPException(422, "Uno de los grupos de origen no existe.")
        db.execute(
            f"""
            INSERT INTO grade_redemption_rules (course_id, {RULE_COLUMNS})
            VALUES (%(course)s, %(assessment)s, %(points_per_step)s, %(step_milli)s,
                    %(max_bonus_milli)s, %(minimum_grade_milli)s)
            ON CONFLICT (course_id) DO UPDATE SET assessment = EXCLUDED.assessment,
                points_per_step = EXCLUDED.points_per_step, step_milli = EXCLUDED.step_milli,
                max_bonus_milli = EXCLUDED.max_bonus_milli, minimum_grade_milli = EXCLUDED.minimum_grade_milli
            """,
            {**settings, "course": course_id},
        )
        db.execute("DELETE FROM grade_redemption_sources WHERE course_id = %s", (course_id,))
        db.execute(
            "INSERT INTO grade_redemption_sources (course_id, source_course_id) SELECT %s, unnest(%s::uuid[])",
            (course_id, body.accepted_course_ids),
        )
        return {**settings, "locked": False}


@router.put("/courses/{course_id}/grade-redemption/students/{student_id}")
def record_grade(course_id: UUID, student_id: UUID, body: SimulatedGrade, account: CurrentAccount, db: Database):
    with db.transaction():
        course_access(db, course_id, account, lock="FOR SHARE OF s", faculty_only=True)
        enrollment = db.execute(
            "SELECT 1 FROM enrollments WHERE course_id = %s AND account_id = %s",
            (course_id, student_id),
        ).fetchone()
        if not enrollment:
            raise HTTPException(404, "El estudiante no tiene matrícula confirmada en este grupo.")
        lock_student_wallet(db, student_id)
        previous = grade_progress(db, course_id, student_id)
        if previous and previous["base_grade_milli"] != body.base_grade_milli:
            if has_active_redemptions(db, course_id, student_id):
                raise HTTPException(409, "La nota base se conserva mientras haya un canje pendiente o aprobado.")
        grade = db.execute(
            """
            INSERT INTO simulated_grades (course_id, student_id, base_grade_milli, recorded_by)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (course_id, student_id) DO UPDATE SET
                base_grade_milli = EXCLUDED.base_grade_milli, recorded_by = EXCLUDED.recorded_by
            RETURNING student_id, base_grade_milli
            """,
            (course_id, student_id, body.base_grade_milli, account.id),
        ).fetchone()
        return {**grade, "locked": has_active_redemptions(db, course_id, student_id)}


@router.post("/courses/{course_id}/grade-redemption/requests", status_code=201)
def request_redemption(course_id: UUID, body: RedemptionInput, account: CurrentAccount, db: Database):
    if account.role != "student":
        raise HTTPException(403, "La solicitud de canje es para estudiantes matriculados.")
    with db.transaction():
        course_access(db, course_id, account, lock="FOR SHARE OF s")
        lock_student_wallet(db, account.id)
        previous = db.execute(
            "SELECT id, course_id, steps FROM grade_redemptions WHERE student_id = %s AND request_key = %s",
            (account.id, body.request_id),
        ).fetchone()
        if previous:
            if (previous["course_id"], previous["steps"]) != (course_id, body.steps):
                raise HTTPException(409, "El identificador corresponde a otra solicitud.")
            return request_detail(db, previous["id"])

        rule = get_rule(db, course_id)
        grade = grade_progress(db, course_id, account.id)
        if not rule or not grade:
            raise HTTPException(409, "El docente debe configurar el canje y registrar tu nota simulada.")
        if grade["has_pending"]:
            raise HTTPException(409, "Ya tienes una solicitud pendiente en este grupo.")
        if rule["minimum_grade_milli"] is not None and grade["base_grade_milli"] < rule["minimum_grade_milli"]:
            raise HTTPException(409, "La nota base no alcanza el mínimo definido por tu docente.")
        boost = body.steps * rule["step_milli"]
        if boost > bonus_remaining(rule, grade):
            raise HTTPException(409, "El ajuste supera el tope del grupo o la nota máxima de 5,000.")
        points = body.steps * rule["points_per_step"]
        lots = eligible_lots(db, account.id, course_id)
        if points > sum(lot["available"] for lot in lots):
            raise HTTPException(409, "Tu saldo de Points de orígenes aceptados no alcanza para este ajuste.")

        before = grade["simulated_grade_milli"]
        created = db.execute(
            """
            INSERT INTO grade_redemptions (request_key, course_id, student_id, assessment, steps, points, boost_milli,
                                           grade_before_milli, grade_after_milli)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (body.request_id, course_id, account.id, rule["assessment"], body.steps, points,
             boost, before, before + boost),
        ).fetchone()
        remaining = points
        with db.cursor() as cursor:
            debits = []
            for lot in lots:
                applied = min(remaining, lot["available"])
                debits.append((created["id"], lot["id"], applied))
                remaining -= applied
                if not remaining:
                    break
            cursor.executemany(
                "INSERT INTO grade_redemption_debits (redemption_id, movement_id, points) VALUES (%s, %s, %s)",
                debits,
            )
        faculty_id = db.execute(
            "SELECT faculty_id FROM course_sections WHERE id = %s", (course_id,),
        ).fetchone()["faculty_id"]
        record_notification(db, faculty_id, f"redemption:{created['id']}:requested",
                            "redemption_requested", course_id=course_id)
        return request_detail(db, created["id"])


@router.put("/courses/{course_id}/grade-redemption/requests/{redemption_id}/review")
def review_redemption(course_id: UUID, redemption_id: UUID, body: RedemptionReview,
                      account: CurrentAccount, db: Database):
    reason = body.reason or None
    if body.decision == "rejected" and not reason:
        raise HTTPException(422, "Escribe un motivo para rechazar el canje.")
    with db.transaction():
        course_access(db, course_id, account, lock="FOR SHARE OF s", faculty_only=True)
        target = db.execute(
            "SELECT student_id FROM grade_redemptions WHERE course_id = %s AND id = %s",
            (course_id, redemption_id),
        ).fetchone()
        if not target:
            raise HTTPException(404, "No encontramos la solicitud de canje.")
        lock_student_wallet(db, target["student_id"])
        request = request_detail(db, redemption_id)
        if request["status"] != "pending":
            if (request["status"], request["reason"]) == (body.decision, reason):
                return request
            raise HTTPException(409, "La solicitud ya fue revisada.")
        db.execute(
            """
            UPDATE grade_redemptions
            SET status = %s, reason = %s, reviewed_by = %s, reviewed_at = clock_timestamp()
            WHERE id = %s
            """,
            (body.decision, reason, account.id, redemption_id),
        )
        record_notification(db, target["student_id"], f"redemption:{redemption_id}:reviewed",
                            f"redemption_{body.decision}", course_id=course_id)
        return request_detail(db, redemption_id)
