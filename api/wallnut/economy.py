from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, StringConstraints, model_validator

from .campus import Admin
from .database import Database
from .identity import CurrentAccount
from .workshops import is_assigned_faculty, load_workshop, require_active_workshop

router = APIRouter(tags=["Economía"])
PositiveAmount = Annotated[int, Field(strict=True, ge=1, le=1_000_000)]
RewardAmount = Annotated[int, Field(strict=True, ge=0, le=1_000_000)]
Goal = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
POLICY_FIELDS = ("attendee_points, facilitator_points, goal_description, goal_coins, coin_cost, "
                 "conversion_points, points_scope")
MOVEMENTS = """
    SELECT m.id, m.kind, m.points, m.coins, s.title AS course, c.title AS workshop, m.created_at
    FROM wallet_movements m
    JOIN workshops w ON w.id = m.workshop_id JOIN workshop_calls c ON c.id = w.call_id
    JOIN course_sections s ON s.id = c.course_id
"""
WALLET_ENTRIES = MOVEMENTS + """
    WHERE m.student_id = %(student)s
    UNION ALL
    SELECT r.id, 'grade_redemption', -r.points, 0, s.title, NULL, r.reviewed_at
    FROM grade_redemptions r JOIN course_sections s ON s.id = r.course_id
    WHERE r.student_id = %(student)s AND r.status = 'approved'
    UNION ALL
    SELECT shop.id, 'ardy_purchase', 0, -shop.price, shop.item_name, NULL, shop.created_at
    FROM ardy_item_purchases shop WHERE shop.student_id = %(student)s
    UNION ALL
    SELECT n.id, 'ardy_nut', 0, -n.price, 'Nuez de Ardy', NULL, n.created_at
    FROM ardy_nuts n WHERE n.student_id = %(student)s
    UNION ALL
    SELECT p.id, 'coin_sent', 0, -p.amount, recipient.display_name, NULL, p.paid_at
    FROM coin_payment_requests p JOIN accounts recipient ON recipient.id = p.recipient_id
    WHERE p.payer_id = %(student)s AND p.paid_at IS NOT NULL
    UNION ALL
    SELECT p.id, 'coin_received', 0, p.amount, payer.display_name, NULL, p.paid_at
    FROM coin_payment_requests p JOIN accounts payer ON payer.id = p.payer_id
    WHERE p.recipient_id = %(student)s AND p.paid_at IS NOT NULL
"""


class AllocationInput(BaseModel):
    points: PositiveAmount
    request_id: UUID


class WorkshopEconomy(BaseModel):
    attendee_points: RewardAmount
    facilitator_points: RewardAmount
    goal_description: Goal | None = None
    goal_coins: PositiveAmount | None = None
    coin_cost: PositiveAmount | None = None
    conversion_points: PositiveAmount | None = None
    points_scope: Literal["course_only", "accepted_courses"] = "course_only"

    @model_validator(mode="after")
    def validate_goal(self):
        fields = (self.goal_description, self.goal_coins, self.coin_cost, self.conversion_points)
        if any(value is None for value in fields) and any(value is not None for value in fields):
            raise ValueError("Completa los cuatro campos de la meta o déjalos todos vacíos.")
        return self


def get_policy(db, workshop_id):
    return db.execute(
        f"SELECT {POLICY_FIELDS} FROM workshop_economies WHERE workshop_id = %s",
        (workshop_id,),
    ).fetchone()


def take_points(db, faculty_id, amount):
    debited = db.execute(
        """
        UPDATE faculty_point_budgets SET available_points = available_points - %s
        WHERE faculty_id = %s AND available_points >= %s RETURNING faculty_id
        """,
        (amount, faculty_id, amount),
    ).fetchone()
    return debited is not None


def require_faculty(workshop, account):
    if not is_assigned_faculty(workshop, account):
        raise HTTPException(403, "Solo el docente asignado puede gestionar esta recompensa.")


def require_student(account):
    if account.role != "student":
        raise HTTPException(403, "La billetera y el canje están disponibles para estudiantes.")


def lock_evidence(db, workshop_id, evidence_id):
    evidence = db.execute(
        """
        SELECT id, student_id, status FROM workshop_evidence
        WHERE workshop_id = %s AND id = %s FOR UPDATE
        """,
        (workshop_id, evidence_id),
    ).fetchone()
    if not evidence:
        raise HTTPException(404, "No encontramos la evidencia.")
    return evidence


def require_approved(evidence):
    if evidence["status"] != "approved":
        raise HTTPException(409, "Primero se debe aprobar la evidencia del taller.")


def lock_student_wallet(db, student_id):
    # Los abonos y gastos en Coins comparten este bloqueo aunque provengan de distintos talleres.
    db.execute("SELECT id FROM accounts WHERE id = %s FOR NO KEY UPDATE", (student_id,))


def movement_for(db, evidence_id, kind):
    return db.execute(MOVEMENTS + " WHERE m.evidence_id = %s AND m.kind = %s",
                      (evidence_id, kind)).fetchone()


def add_movement(db, workshop, evidence, kind, *, points=0, coins=0):
    created = db.execute(
        """
        INSERT INTO wallet_movements (workshop_id, evidence_id, student_id, faculty_id, kind, points, coins)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
        """,
        (workshop["id"], evidence["id"], evidence["student_id"], workshop["faculty_id"],
         kind, points, coins),
    ).fetchone()
    return db.execute(MOVEMENTS + " WHERE m.id = %s", (created["id"],)).fetchone()


def credit_approved_evidence(db, workshop, evidence, *, strict=False):
    # La llamada mantiene bloqueadas la evidencia y la configuración del taller.
    previous = movement_for(db, evidence["id"], "evidence_reward")
    if previous:
        return previous
    policy = get_policy(db, workshop["id"])
    reward_key = (
        "facilitator_points" if workshop["facilitator_id"] == evidence["student_id"]
        else "attendee_points"
    )
    reward = policy[reward_key] if policy else 0
    if not reward:
        if strict:
            raise HTTPException(409, "Esta evidencia no tiene Points configurados.")
        return None
    if not take_points(db, workshop["faculty_id"], reward):
        if strict:
            raise HTTPException(409, "El cupo docente no tiene Points suficientes.")
        return None
    return add_movement(db, workshop, evidence, "evidence_reward", points=reward)


def wallet_totals(db, student_id):
    return db.execute(
        """
        WITH earned AS (
            SELECT coalesce(sum(points), 0) AS points, coalesce(sum(coins), 0) AS coins
            FROM wallet_movements WHERE student_id = %(student)s
        ), used AS (
            SELECT coalesce(sum(points) FILTER (WHERE status IN ('approved', 'pending')), 0)
                       AS committed_points,
                   coalesce(sum(points) FILTER (WHERE status = 'pending'), 0) AS reserved_points
            FROM grade_redemptions WHERE student_id = %(student)s
        ), campus_coins AS (
            SELECT coalesce(sum(delta), 0) AS balance
            FROM (
                SELECT amount AS delta FROM coin_payment_requests
                WHERE recipient_id = %(student)s AND paid_at IS NOT NULL
                UNION ALL
                SELECT -amount FROM coin_payment_requests WHERE payer_id = %(student)s AND paid_at IS NOT NULL
                UNION ALL
                SELECT -price FROM ardy_item_purchases WHERE student_id = %(student)s
                UNION ALL
                SELECT -price FROM ardy_nuts WHERE student_id = %(student)s
            ) deltas
        )
        SELECT (earned.points - used.committed_points)::bigint AS points,
               (earned.coins + campus_coins.balance)::bigint AS coins,
               used.reserved_points::bigint AS reserved_points
        FROM earned, used, campus_coins
        """,
        {"student": student_id},
    ).fetchone()


@router.get("/faculty-budgets")
def list_budgets(account: CurrentAccount, db: Database):
    if account.role not in ("admin", "faculty"):
        raise HTTPException(403, "Consulta de cupos reservada para docentes y administración.")
    return db.execute(
        """
        SELECT a.id AS faculty_id, a.display_name, coalesce(b.available_points, 0) AS available_points
        FROM accounts a LEFT JOIN faculty_point_budgets b ON b.faculty_id = a.id
        WHERE a.role = 'faculty' AND (%s OR a.id = %s)
        ORDER BY a.display_name, a.id
        """,
        (account.role == "admin", account.id),
    ).fetchall()


def record_allocation(db, faculty_id, admin_id, points, request_id):
    created = db.execute(
        """
        INSERT INTO point_allocations (request_id, faculty_id, admin_id, points)
        VALUES (%s, %s, %s, %s) ON CONFLICT (request_id) DO NOTHING
        RETURNING id, faculty_id, points
        """,
        (request_id, faculty_id, admin_id, points),
    ).fetchone()
    if created:
        db.execute(
            """
            INSERT INTO faculty_point_budgets (faculty_id, available_points) VALUES (%s, %s)
            ON CONFLICT (faculty_id) DO UPDATE SET
                available_points = faculty_point_budgets.available_points + EXCLUDED.available_points
            """,
            (faculty_id, points),
        )
        return created
    existing = db.execute(
        "SELECT id, faculty_id, points FROM point_allocations WHERE request_id = %s",
        (request_id,),
    ).fetchone()
    if not existing or (existing["faculty_id"], existing["points"]) != (faculty_id, points):
        raise HTTPException(409, "El identificador ya corresponde a otra asignación.")
    return existing


@router.post("/faculty-budgets/{faculty_id}/allocations", status_code=201)
def allocate(faculty_id: UUID, body: AllocationInput, account: Admin, db: Database):
    with db.transaction():
        faculty = db.execute(
            "SELECT id FROM accounts WHERE id = %s AND role = 'faculty'", (faculty_id,)
        ).fetchone()
        if not faculty:
            raise HTTPException(404, "No encontramos un docente habilitado con esa cuenta.")
        return record_allocation(db, faculty_id, account.id, body.points, body.request_id)


@router.get("/workshops/{workshop_id}/economy")
def read_workshop_policy(workshop_id: UUID, account: CurrentAccount, db: Database, response: Response):
    with db.transaction():
        load_workshop(db, workshop_id)
        response.headers["Cache-Control"] = "private, no-store"
        return get_policy(db, workshop_id)


@router.put("/workshops/{workshop_id}/economy")
def save_workshop_policy(workshop_id: UUID, body: WorkshopEconomy, account: CurrentAccount, db: Database):
    with db.transaction():
        workshop = load_workshop(db, workshop_id, exclusive_lock=True)
        require_faculty(workshop, account)
        require_active_workshop(workshop)
        existing = get_policy(db, workshop_id)
        if existing == body.model_dump():
            return existing
        if db.execute("SELECT 1 FROM wallet_movements WHERE workshop_id = %s LIMIT 1",
                      (workshop_id,)).fetchone():
            raise HTTPException(409, "Las recompensas ya están en uso y conservan sus reglas.")
        return db.execute(
            f"""
            INSERT INTO workshop_economies (workshop_id, {POLICY_FIELDS})
            VALUES (%(workshop_id)s, %(attendee_points)s, %(facilitator_points)s,
                    %(goal_description)s, %(goal_coins)s, %(coin_cost)s, %(conversion_points)s,
                    %(points_scope)s)
            ON CONFLICT (workshop_id) DO UPDATE SET
                attendee_points = EXCLUDED.attendee_points,
                facilitator_points = EXCLUDED.facilitator_points,
                goal_description = EXCLUDED.goal_description,
                goal_coins = EXCLUDED.goal_coins,
                coin_cost = EXCLUDED.coin_cost,
                conversion_points = EXCLUDED.conversion_points,
                points_scope = EXCLUDED.points_scope
            RETURNING {POLICY_FIELDS}
            """,
            {"workshop_id": workshop_id, **body.model_dump()},
        ).fetchone()


@router.post("/workshops/{workshop_id}/evidence/{evidence_id}/reward")
def retry_reward(workshop_id: UUID, evidence_id: UUID, account: CurrentAccount, db: Database):
    with db.transaction():
        evidence = lock_evidence(db, workshop_id, evidence_id)
        workshop = load_workshop(db, workshop_id)
        require_faculty(workshop, account)
        require_approved(evidence)
        return credit_approved_evidence(db, workshop, evidence, strict=True)


@router.post("/workshops/{workshop_id}/evidence/{evidence_id}/goal")
def verify_goal(workshop_id: UUID, evidence_id: UUID, account: CurrentAccount, db: Database):
    with db.transaction():
        evidence = lock_evidence(db, workshop_id, evidence_id)
        workshop = load_workshop(db, workshop_id)
        require_faculty(workshop, account)
        require_approved(evidence)
        policy = get_policy(db, workshop_id)
        if not policy or not policy["goal_description"]:
            raise HTTPException(409, "Configura primero una meta académica para el taller.")
        previous = movement_for(db, evidence_id, "goal_coins")
        if previous:
            return previous
        lock_student_wallet(db, evidence["student_id"])
        return add_movement(db, workshop, evidence, "goal_coins", coins=policy["goal_coins"])


@router.post("/workshops/{workshop_id}/evidence/{evidence_id}/convert")
def convert_coins(workshop_id: UUID, evidence_id: UUID, account: CurrentAccount, db: Database):
    require_student(account)
    with db.transaction():
        evidence = lock_evidence(db, workshop_id, evidence_id)
        if evidence["student_id"] != account.id:
            raise HTTPException(403, "Solo puedes canjear Coins con tus propias evidencias.")
        require_approved(evidence)
        previous = movement_for(db, evidence_id, "coin_conversion")
        if previous:
            return previous
        if not movement_for(db, evidence_id, "goal_coins"):
            raise HTTPException(409, "El docente debe verificar tu meta académica antes del canje.")

        workshop = load_workshop(db, workshop_id)
        policy = get_policy(db, workshop_id)
        lock_student_wallet(db, account.id)
        if wallet_totals(db, account.id)["coins"] < policy["coin_cost"]:
            raise HTTPException(409, "Tu billetera no tiene Coins suficientes para este canje.")
        if not take_points(db, workshop["faculty_id"], policy["conversion_points"]):
            raise HTTPException(409, "El cupo docente no tiene Points suficientes para este canje.")
        return add_movement(db, workshop, evidence, "coin_conversion",
                            points=policy["conversion_points"], coins=-policy["coin_cost"])


@router.get("/wallet")
def read_wallet(account: CurrentAccount, db: Database, response: Response):
    require_student(account)
    with db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        totals = wallet_totals(db, account.id)
        movements = db.execute(
            "SELECT * FROM (" + WALLET_ENTRIES + """) entries
            ORDER BY created_at DESC, id DESC, kind DESC LIMIT 50
            """,
            {"student": account.id},
        ).fetchall()
        conversions = db.execute(
            """
            SELECT e.workshop_id, e.id AS evidence_id, c.title AS workshop, s.title AS course,
                   p.goal_description AS goal, p.coin_cost, p.conversion_points AS points,
                   EXISTS (SELECT 1 FROM wallet_movements result WHERE result.evidence_id = e.id
                           AND result.kind = 'coin_conversion') AS converted
            FROM wallet_movements goal
            JOIN workshop_evidence e ON e.id = goal.evidence_id
            JOIN workshop_economies p ON p.workshop_id = goal.workshop_id
            JOIN workshops w ON w.id = goal.workshop_id
            JOIN workshop_calls c ON c.id = w.call_id
            JOIN course_sections s ON s.id = c.course_id
            WHERE goal.student_id = %s AND goal.kind = 'goal_coins'
            ORDER BY goal.created_at DESC, goal.id DESC
            """,
            (account.id,),
        ).fetchall()
    response.headers["Cache-Control"] = "private, no-store"
    return {**totals, "movements": movements, "conversions": conversions}
