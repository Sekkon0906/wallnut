from secrets import choice, randbelow
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from .coin_shop import NUT_PRIZES
from .database import Database
from .economy import lock_student_wallet, require_student, wallet_totals
from .identity import CurrentAccount

router = APIRouter(prefix="/ardy-nuts", tags=["Nueces de Ardy"])
PRICE = 4
RARITY_WEIGHTS = {"normal": 60, "special": 25, "epic": 12, "legendary": 3}


class Purchase(BaseModel):
    id: UUID


class Tap(BaseModel):
    step: Annotated[int, Field(strict=True, ge=1, le=3)]


def available_prizes(db, student_id):
    drawn = {row["item_id"] for row in db.execute(
        "SELECT item_id FROM ardy_nuts WHERE student_id = %s AND taps = 3", (student_id,),
    )}
    return {
        rarity: [item_id for item_id, item in NUT_PRIZES.items()
                 if item["rarity"] == rarity and item_id not in drawn]
        for rarity in RARITY_WEIGHTS
    }


def odds(prizes):
    return {rarity: weight if prizes[rarity] else 0 for rarity, weight in RARITY_WEIGHTS.items()}


def draw(prizes):
    weights = odds(prizes)
    total = sum(weights.values())
    if not total:
        raise HTTPException(409, "Ya tienes todos los artículos de estas nueces.")
    roll = randbelow(total)
    for rarity, weight in weights.items():
        if roll < weight:
            return choice(prizes[rarity])
        roll -= weight


def opening_view(row):
    prize = NUT_PRIZES[row["item_id"]]
    return {
        "id": row["id"], "taps": row["taps"],
        "rarity": prize["rarity"] if row["taps"] else None,
        "reward": {"id": row["item_id"], **prize, "owned": True} if row["taps"] == 3 else None,
    }


@router.get("")
def read_nuts(account: CurrentAccount, db: Database, response: Response):
    require_student(account)
    with db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        latest = db.execute(
            """
            SELECT id, item_id, taps FROM ardy_nuts WHERE student_id = %s
            ORDER BY created_at DESC, id DESC LIMIT 1
            """,
            (account.id,),
        ).fetchone()
        prizes = available_prizes(db, account.id)
        coins = wallet_totals(db, account.id)["coins"]
    response.headers["Cache-Control"] = "private, no-store"
    return {"price": PRICE, "coins": coins, "odds": odds(prizes),
            "latest": opening_view(latest) if latest else None}


@router.post("")
def buy_nut(body: Purchase, account: CurrentAccount, db: Database, response: Response):
    require_student(account)
    response.headers["Cache-Control"] = "private, no-store"
    with db.transaction():
        lock_student_wallet(db, account.id)
        previous = db.execute(
            """
            SELECT id, item_id, taps FROM ardy_nuts WHERE student_id = %s AND (id = %s OR taps < 3)
            ORDER BY (id = %s) DESC LIMIT 1
            """,
            (account.id, body.id, body.id),
        ).fetchone()
        if previous:
            if previous["id"] != body.id:
                raise HTTPException(409, "Ya tienes una nuez pendiente. Continúa su apertura.")
            return opening_view(previous)
        if wallet_totals(db, account.id)["coins"] < PRICE:
            raise HTTPException(409, "Tu billetera no tiene suficientes Coins para abrir una nuez.")
        item_id = draw(available_prizes(db, account.id))
        created = db.execute(
            """
            INSERT INTO ardy_nuts (id, student_id, item_id, price) VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING RETURNING id, item_id, taps
            """,
            (body.id, account.id, item_id, PRICE),
        ).fetchone()
        if not created:
            raise HTTPException(409, "Ese código de compra ya está en uso. Actualiza la tienda.")
        return opening_view(created)


@router.put("/{nut_id}/tap")
def tap_nut(nut_id: UUID, body: Tap, account: CurrentAccount, db: Database, response: Response):
    require_student(account)
    response.headers["Cache-Control"] = "private, no-store"
    with db.transaction():
        nut = db.execute(
            "SELECT id, item_id, taps FROM ardy_nuts WHERE id = %s AND student_id = %s FOR UPDATE",
            (nut_id, account.id),
        ).fetchone()
        if not nut:
            raise HTTPException(404, "No encontramos esta nuez.")
        if body.step > nut["taps"] + 1:
            raise HTTPException(409, "Completa el toque anterior antes de continuar.")
        if body.step > nut["taps"]:
            db.execute("UPDATE ardy_nuts SET taps = %s WHERE id = %s", (body.step, nut_id))
            nut["taps"] = body.step
        return opening_view(nut)
