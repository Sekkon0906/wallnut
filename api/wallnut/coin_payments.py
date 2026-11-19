from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from .database import Database
from .economy import require_student, wallet_totals
from .identity import CurrentAccount

router = APIRouter(prefix="/coin-payments", tags=["Pagos de Coins"])
PAYMENT = """
    SELECT p.id, p.recipient_id, p.payer_id, a.display_name AS recipient, p.amount,
           p.expires_at, p.paid_at, p.expires_at <= clock_timestamp() AS expired
    FROM coin_payment_requests p JOIN accounts a ON a.id = p.recipient_id
"""


class Charge(BaseModel):
    id: UUID
    amount: Annotated[int, Field(strict=True, ge=1, le=1000)]


def find_payment(db, payment_id, *, lock=False):
    payment = db.execute(
        PAYMENT + " WHERE p.id = %s" + (" FOR UPDATE OF p" if lock else ""), (payment_id,),
    ).fetchone()
    if not payment:
        raise HTTPException(404, "No encontramos la solicitud de Coins.")
    return payment


def payment_view(payment, account_id, response):
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "id": payment["id"],
        "recipient": payment["recipient"],
        "amount": payment["amount"],
        "expires_at": payment["expires_at"],
        "paid_at": payment["paid_at"],
        "status": "paid" if payment["paid_at"] else "expired" if payment["expired"] else "pending",
        "can_pay": not payment["paid_at"] and not payment["expired"] and payment["recipient_id"] != account_id,
        "is_recipient": payment["recipient_id"] == account_id,
        "paid_by_me": payment["paid_at"] is not None and payment["payer_id"] == account_id,
    }


@router.get("")
def recent_payments(account: CurrentAccount, db: Database, response: Response):
    require_student(account)
    response.headers["Cache-Control"] = "private, no-store"
    payments = db.execute(
        PAYMENT + """
        WHERE p.recipient_id = %(account)s OR p.payer_id = %(account)s
        ORDER BY (p.paid_at IS NULL AND p.expires_at > statement_timestamp()) DESC,
                 coalesce(p.paid_at, p.expires_at) DESC, p.id DESC
        LIMIT 10
        """, {"account": account.id},
    ).fetchall()
    return [payment_view(payment, account.id, response) for payment in payments]


@router.post("")
def request_payment(body: Charge, account: CurrentAccount, db: Database, response: Response):
    require_student(account)
    with db.transaction():
        db.execute(
            "INSERT INTO coin_payment_requests (id, recipient_id, amount) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (body.id, account.id, body.amount),
        )
        payment = find_payment(db, body.id)
        if (payment["recipient_id"], payment["amount"]) != (account.id, body.amount):
            raise HTTPException(409, "Ese código ya está asociado a otra solicitud.")
    return payment_view(payment, account.id, response)


@router.get("/{payment_id}")
def read_payment(payment_id: UUID, account: CurrentAccount, db: Database, response: Response):
    require_student(account)
    return payment_view(find_payment(db, payment_id), account.id, response)


@router.post("/{payment_id}/pay")
def pay(payment_id: UUID, account: CurrentAccount, db: Database, response: Response):
    require_student(account)
    with db.transaction():
        payment = find_payment(db, payment_id, lock=True)
        if payment["payer_id"] == account.id:
            return payment_view(payment, account.id, response)
        if payment["paid_at"] or payment["expired"] or payment["recipient_id"] == account.id:
            raise HTTPException(409, "Esta solicitud de Coins ya no está disponible para pagar.")
        # Adquiere ambos bloqueos en orden de ID, incluso si hay pagos cruzados.
        db.execute(
            "SELECT id FROM accounts WHERE id IN (%s, %s) ORDER BY id FOR NO KEY UPDATE",
            (account.id, payment["recipient_id"]),
        ).fetchall()
        if wallet_totals(db, account.id)["coins"] < payment["amount"]:
            raise HTTPException(409, "Tu billetera no tiene suficientes Coins para este pago.")
        updated = db.execute(
            """
            UPDATE coin_payment_requests SET payer_id = %s, paid_at = stamp.at
            FROM (SELECT clock_timestamp() AS at) stamp
            WHERE id = %s AND stamp.at < expires_at RETURNING paid_at, payer_id
            """,
            (account.id, payment_id),
        ).fetchone()
        if not updated:
            raise HTTPException(409, "La solicitud de Coins venció.")
        payment.update(updated)
    return payment_view(payment, account.id, response)
