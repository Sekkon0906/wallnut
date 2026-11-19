from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import AwareDatetime, BaseModel

from .database import Database
from .economy import MOVEMENTS
from .identity import CurrentAccount

router = APIRouter(tags=["Historial de cupos docentes"])
MovementKind = Literal["allocation", "evidence_reward", "coin_conversion"]


class BudgetCursor(BaseModel):
    created_at: AwareDatetime
    id: UUID
    kind: MovementKind


class BudgetMovement(BudgetCursor):
    points: int
    actor: str | None
    course: str | None
    workshop: str | None


class BudgetLedger(BaseModel):
    faculty_id: UUID
    display_name: str
    generated_at: AwareDatetime
    allocated_points: int
    awarded_points: int
    converted_points: int
    available_points: int
    difference: int
    entries: list[BudgetMovement]
    next_cursor: BudgetCursor | None


@router.get("/faculty-budgets/{faculty_id}/ledger", response_model=BudgetLedger)
def budget_ledger(
    faculty_id: UUID, account: CurrentAccount, db: Database, response: Response,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    before: AwareDatetime | None = None,
    before_id: UUID | None = None,
    before_kind: MovementKind | None = None,
):
    if account.role != "admin" and not (account.role == "faculty" and account.id == faculty_id):
        raise HTTPException(403, "Puedes consultar el historial de tu propio cupo docente.")
    supplied = sum(value is not None for value in (before, before_id, before_kind))
    if supplied not in (0, 3):
        raise HTTPException(422, "Completa la referencia de la página anterior.")
    parameters = {"faculty": faculty_id, "before": before, "before_id": before_id,
                  "before_kind": before_kind, "limit": limit + 1}
    with db.transaction():
        # Totals and history must see the same committed allocations and rewards.
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        summary = db.execute(
            """
            SELECT a.id AS faculty_id, a.display_name, statement_timestamp() AS generated_at,
                   coalesce(b.available_points, 0) AS available_points,
                   allocations.allocated_points, rewards.awarded_points, rewards.converted_points
            FROM accounts a LEFT JOIN faculty_point_budgets b ON b.faculty_id = a.id
            CROSS JOIN (
                SELECT coalesce(sum(points), 0) AS allocated_points
                FROM point_allocations WHERE faculty_id = %(faculty)s
            ) allocations
            CROSS JOIN (
                SELECT coalesce(sum(points) FILTER (WHERE kind = 'evidence_reward'), 0) AS awarded_points,
                       coalesce(sum(points) FILTER (WHERE kind = 'coin_conversion'), 0) AS converted_points
                FROM wallet_movements WHERE faculty_id = %(faculty)s
            ) rewards
            WHERE a.id = %(faculty)s AND a.role = 'faculty'
            """, parameters,
        ).fetchone()
        if not summary:
            raise HTTPException(404, "No encontramos el cupo de ese docente.")
        candidates = db.execute(
            """
            WITH entries AS (
                SELECT p.id, p.created_at, 'allocation' AS kind, p.points,
                       a.display_name AS actor, NULL::text AS course, NULL::text AS workshop
                FROM point_allocations p JOIN accounts a ON a.id = p.admin_id
                WHERE p.faculty_id = %(faculty)s
                UNION ALL
                SELECT m.id, m.created_at, m.kind, -m.points, NULL::text, m.course, m.workshop
                FROM (""" + MOVEMENTS + """
                    WHERE m.faculty_id = %(faculty)s AND m.points > 0
                ) m
            )
            SELECT * FROM entries
            WHERE %(before)s::timestamptz IS NULL
               OR (created_at, id, kind) < (%(before)s, %(before_id)s::uuid, %(before_kind)s::text)
            ORDER BY created_at DESC, id DESC, kind DESC LIMIT %(limit)s
            """, parameters,
        ).fetchall()
    entries = candidates[:limit]
    difference = (summary["allocated_points"] - summary["awarded_points"]
                  - summary["converted_points"] - summary["available_points"])
    response.headers["Cache-Control"] = "private, no-store"
    return {**summary, "difference": difference, "entries": entries,
            "next_cursor": BudgetCursor.model_validate(entries[-1]) if len(candidates) > limit else None}
