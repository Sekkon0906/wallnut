from fastapi import APIRouter, HTTPException, Response

from .database import Database
from .economy import lock_student_wallet, require_student, wallet_totals
from .identity import CurrentAccount

router = APIRouter(tags=["Tienda de Ardy"])
CATALOG = {
    "jacket-purple": {"name": "Chaqueta violeta", "price": 6, "slot": "outfit", "value": "purple_jacket"},
    "cap-gold": {"name": "Gorra dorada", "price": 4, "slot": "headwear", "value": "gold_cap"},
}
NUT_PRIZES = {
    "sage_hoodie": {"name": "Buzo salvia", "slot": "outfit", "value": "sage_hoodie", "rarity": "normal"},
    "rust_cap": {"name": "Gorra terracota", "slot": "headwear", "value": "rust_cap", "rarity": "normal"},
    "mint_helmet": {"name": "Casco menta", "slot": "headwear", "value": "mint_helmet", "rarity": "special"},
    "reef_jacket": {"name": "Chaqueta arrecife", "slot": "outfit", "value": "reef_jacket", "rarity": "special"},
    "nebula_jacket": {"name": "Chaqueta nebulosa", "slot": "outfit", "value": "nebula_jacket", "rarity": "epic"},
    "moon_cap": {"name": "Gorra lunar", "slot": "headwear", "value": "moon_cap", "rarity": "epic"},
    "solar_jacket": {"name": "Chaqueta eclipse solar", "slot": "outfit", "value": "solar_jacket", "rarity": "legendary"},
    "crown": {"name": "Corona dorada", "slot": "headwear", "value": "crown", "rarity": "legendary"},
}
EQUIPMENT = {**CATALOG, **NUT_PRIZES}


def owned_items(db, student_id):
    return {row["item_id"] for row in db.execute(
        """
        SELECT item_id FROM ardy_item_purchases WHERE student_id = %(student)s
        UNION ALL
        SELECT item_id FROM ardy_nuts WHERE student_id = %(student)s AND taps = 3
        """,
        {"student": student_id},
    )}


@router.get("/ardy-shop")
def read_shop(account: CurrentAccount, db: Database, response: Response):
    require_student(account)
    owned = owned_items(db, account.id)
    response.headers["Cache-Control"] = "private, no-store"
    return [
        {"id": item_id, **item, "owned": item_id in owned}
        for item_id, item in EQUIPMENT.items()
        if item_id in CATALOG or item_id in owned
    ]


@router.post("/ardy-shop/{item_id}")
def buy_item(item_id: str, account: CurrentAccount, db: Database):
    require_student(account)
    item = CATALOG.get(item_id)
    if not item:
        raise HTTPException(404, "Este artículo no está disponible.")
    with db.transaction():
        lock_student_wallet(db, account.id)
        if item_id not in owned_items(db, account.id):
            if wallet_totals(db, account.id)["coins"] < item["price"]:
                raise HTTPException(409, "Tu billetera no tiene suficientes Coins para este artículo.")
            db.execute(
                "INSERT INTO ardy_item_purchases (student_id, item_id, item_name, price) VALUES (%s, %s, %s, %s)",
                (account.id, item_id, item["name"], item["price"]),
            )
    return {"id": item_id, **item, "owned": True}
