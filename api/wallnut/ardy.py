from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .coin_shop import EQUIPMENT, owned_items
from .database import Database
from .identity import CurrentAccount

router = APIRouter(tags=["Ardy y participación"])


class Avatar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    height: Annotated[int, Field(strict=True, ge=85, le=115)] = 100
    build: Literal["slender", "rounded", "athletic"] = "rounded"
    fur: Literal["amber", "chestnut", "gray", "cream"] = "amber"
    texture: Literal["smooth", "wavy", "curly"] = "smooth"
    tail: Literal["curled", "fluffy"] = "curled"
    glasses: Literal["none", "round", "square"] = "none"
    headwear: Literal["none", "cap", "helmet", "gold_cap", "rust_cap", "mint_helmet", "moon_cap", "crown"] = "none"
    outfit: Literal["none", "hoodie", "jacket", "purple_jacket", "sage_hoodie", "reef_jacket",
                    "nebula_jacket", "solar_jacket"] = "hoodie"
    accessory: Literal["none", "chain", "backpack"] = "none"


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    avatar: Avatar
    show_in_ranking: bool
    career: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)] | None = None


class RankEntry(BaseModel):
    student_id: UUID
    display_name: str
    points: int
    activities: int
    position: int
    avatar: Avatar
    is_me: bool


class Ranking(BaseModel):
    entries: list[RankEntry]
    me: RankEntry | None


def student_only(account):
    if account.role != "student":
        raise HTTPException(403, "Mi Ardy está disponible para estudiantes.")


@router.get("/my-ardy", response_model=Profile)
def read_profile(account: CurrentAccount, db: Database, response: Response):
    student_only(account)
    row = db.execute(
        "SELECT avatar, show_in_ranking, career FROM ardy_profiles WHERE student_id = %s",
        (account.id,),
    ).fetchone()
    response.headers["Cache-Control"] = "private, no-store"
    return row or Profile(avatar=Avatar(), show_in_ranking=False)


@router.put("/my-ardy", response_model=Profile)
def save_profile(body: Profile, account: CurrentAccount, db: Database, response: Response):
    student_only(account)
    equipped = {item_id for item_id, item in EQUIPMENT.items()
                if getattr(body.avatar, item["slot"]) == item["value"]}
    if equipped - owned_items(db, account.id):
        raise HTTPException(403, "Adquiere este artículo antes de equiparlo.")
    db.execute(
        """
        INSERT INTO ardy_profiles (student_id, avatar, show_in_ranking, career)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (student_id) DO UPDATE SET avatar = EXCLUDED.avatar,
            show_in_ranking = EXCLUDED.show_in_ranking, career = EXCLUDED.career, updated_at = clock_timestamp()
        """,
        (account.id, Jsonb(body.avatar.model_dump()), body.show_in_ranking, body.career),
    )
    response.headers["Cache-Control"] = "private, no-store"
    return body


@router.get("/participation-ranking", response_model=Ranking)
def participation_ranking(account: CurrentAccount, db: Database, response: Response):
    entries = db.execute(
        """
        WITH participation AS (
            SELECT e.student_id, count(*) AS activities, coalesce(sum(m.points), 0) AS points
            FROM workshop_evidence e
            JOIN ardy_profiles p ON p.student_id = e.student_id AND p.show_in_ranking
            JOIN accounts a ON a.id = e.student_id AND a.role = 'student'
            LEFT JOIN wallet_movements m ON m.evidence_id = e.id AND m.kind = 'evidence_reward'
            WHERE e.status = 'approved'
            GROUP BY e.student_id
        ), ranked AS (
            SELECT participation.*, dense_rank() OVER (ORDER BY points DESC, activities DESC) AS position
            FROM participation
        ), ordered AS (
            SELECT r.*, a.display_name, p.avatar, r.student_id = %(account)s AS is_me,
                   row_number() OVER (ORDER BY r.position, a.display_name, r.student_id) AS row_number
            FROM ranked r JOIN accounts a ON a.id = r.student_id
            JOIN ardy_profiles p ON p.student_id = r.student_id
        )
        SELECT student_id, display_name, points, activities, position, avatar, is_me, row_number
        FROM ordered
        WHERE row_number <= 30 OR is_me ORDER BY row_number
        """,
        {"account": account.id},
    ).fetchall()
    response.headers["Cache-Control"] = "private, no-store"
    return {"entries": [row for row in entries if row["row_number"] <= 30],
            "me": next((row for row in entries if row["is_me"]), None)}
