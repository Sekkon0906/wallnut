from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import AwareDatetime, BaseModel

from .database import Database
from .economy import WALLET_ENTRIES, require_student, wallet_totals
from .identity import CurrentAccount

router = APIRouter(tags=["Historial de la billetera"])
MovementKind = Literal[
    "evidence_reward", "goal_coins", "coin_conversion", "grade_redemption",
    "ardy_purchase", "ardy_nut", "coin_sent", "coin_received",
]


class WalletCursor(BaseModel):
    id: UUID
    created_at: AwareDatetime
    kind: MovementKind


class WalletEntry(WalletCursor):
    points: int
    coins: int
    course: str
    workshop: str | None


class WalletBalances(BaseModel):
    points: int
    coins: int
    reserved_points: int


class HistorySummary(BaseModel):
    generated_at: AwareDatetime
    credited_points: int
    spent_points: int
    credited_coins: int
    spent_coins: int
    points_difference: int
    coins_difference: int


class WalletHistory(BaseModel):
    balances: WalletBalances
    summary: HistorySummary
    movements: list[WalletEntry]
    next_cursor: WalletCursor | None


@router.get("/wallet/history", response_model=WalletHistory)
def history(
    account: CurrentAccount, db: Database, response: Response,
    currency: Literal["all", "points", "coins"] = "all",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    before: AwareDatetime | None = None,
    before_id: UUID | None = None,
    before_kind: MovementKind | None = None,
):
    require_student(account)
    if sum(value is not None for value in (before, before_id, before_kind)) not in (0, 3):
        raise HTTPException(422, "Completa la referencia de la página anterior.")
    parameters = {"student": account.id, "currency": currency, "limit": limit + 1,
                  "before": before, "before_id": before_id, "before_kind": before_kind}
    with db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        balances = wallet_totals(db, account.id)
        summary = db.execute(
            "SELECT statement_timestamp() AS generated_at, "
            "coalesce(sum(points) FILTER (WHERE points > 0), 0) AS credited_points, "
            "coalesce(sum(-points) FILTER (WHERE points < 0), 0) AS spent_points, "
            "coalesce(sum(coins) FILTER (WHERE coins > 0), 0) AS credited_coins, "
            "coalesce(sum(-coins) FILTER (WHERE coins < 0), 0) AS spent_coins "
            "FROM (" + WALLET_ENTRIES + ") entries", parameters,
        ).fetchone()
        candidates = db.execute(
            "SELECT * FROM (" + WALLET_ENTRIES + """) entries
            WHERE (%(currency)s = 'all' OR (%(currency)s = 'points' AND points <> 0)
                   OR (%(currency)s = 'coins' AND coins <> 0))
              AND (%(before)s::timestamptz IS NULL
                   OR (created_at, id, kind) < (%(before)s, %(before_id)s::uuid, %(before_kind)s::text))
            ORDER BY created_at DESC, id DESC, kind DESC LIMIT %(limit)s
            """, parameters,
        ).fetchall()
    movements = candidates[:limit]
    summary["points_difference"] = (summary["credited_points"] - summary["spent_points"]
                                    - balances["reserved_points"] - balances["points"])
    summary["coins_difference"] = summary["credited_coins"] - summary["spent_coins"] - balances["coins"]
    response.headers["Cache-Control"] = "private, no-store"
    return {"balances": balances, "summary": summary, "movements": movements,
            "next_cursor": WalletCursor.model_validate(movements[-1]) if len(candidates) > limit else None}
