from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StringConstraints

from .auth import Database, Member

router = APIRouter(tags=["Puntos"])
Handle = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[a-z0-9_]{3,24}$")]


class Transfer(BaseModel):
    recipient: Handle
    points: Annotated[int, Field(strict=True, ge=1, le=1000000)]
    request_id: UUID


def lock_members(db, member_ids):
    # Siempre se toman en el mismo orden, también en transferencias opuestas.
    db.execute("SELECT id FROM members WHERE id = ANY(%s) ORDER BY id FOR UPDATE", (member_ids,))


def balance(db, member_id):
    return db.execute(
        """
        SELECT
            COALESCE((SELECT sum(points) FROM point_movements WHERE recipient_id = %s), 0)
            - COALESCE((SELECT sum(points) FROM point_movements WHERE sender_id = %s), 0)
            AS balance
        """,
        (member_id, member_id),
    ).fetchone()["balance"]


@router.get("/wallet")
def wallet(member: Member, db: Database):
    member_id = member["id"]
    with db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        current_balance = balance(db, member_id)
        movements = db.execute(
            """
            SELECT p.id, p.kind, p.created_at,
                   CASE WHEN p.sender_id = %(id)s THEN -p.points ELSE p.points END AS points,
                   CASE WHEN p.kind = 'attendance' THEN a.title
                        WHEN p.sender_id = %(id)s THEN recipient.handle
                        ELSE sender.handle END AS label
            FROM point_movements p
            JOIN members recipient ON recipient.id = p.recipient_id
            LEFT JOIN members sender ON sender.id = p.sender_id
            LEFT JOIN activities a ON a.id = p.activity_id
            WHERE p.sender_id = %(id)s OR p.recipient_id = %(id)s
            ORDER BY p.created_at DESC, p.id DESC
            LIMIT 50
            """,
            {"id": member_id},
        ).fetchall()
    return {"balance": current_balance, "movements": movements}


@router.post("/transfers")
def transfer(body: Transfer, member: Member, db: Database):
    if member["role"] != "student":
        raise HTTPException(403, "Los envíos de puntos son para estudiantes.")
    sender_id = member["id"]
    recipient = db.execute(
        "SELECT id FROM members WHERE handle = %s AND role = 'student'", (body.recipient,)
    ).fetchone()
    if not recipient:
        raise HTTPException(404, "No encontramos ese usuario.")
    recipient_id = recipient["id"]
    if sender_id == recipient_id:
        raise HTTPException(422, "Elige otra cuenta para enviar puntos.")

    with db.transaction():
        lock_members(db, [sender_id, recipient_id])
        previous = db.execute(
            """
            SELECT id, recipient_id, points FROM point_movements
            WHERE sender_id = %s AND request_id = %s
            """,
            (sender_id, body.request_id),
        ).fetchone()
        if previous:
            if previous["recipient_id"] != recipient_id or previous["points"] != body.points:
                raise HTTPException(409, "El identificador ya se usó para otro envío.")
            return {"id": previous["id"], "points": previous["points"]}

        if balance(db, sender_id) < body.points:
            raise HTTPException(409, "Tu saldo es insuficiente para este envío.")
        return db.execute(
            """
            INSERT INTO point_movements (kind, sender_id, recipient_id, points, request_id)
            VALUES ('transfer', %s, %s, %s, %s) RETURNING id, points
            """,
            (sender_id, recipient_id, body.points, body.request_id),
        ).fetchone()


@router.get("/ranking")
def ranking(member: Member, db: Database):
    return db.execute(
        """
        SELECT m.handle, m.display_name, sum(p.points) AS points,
               dense_rank() OVER (ORDER BY sum(p.points) DESC) AS position
        FROM point_movements p JOIN members m ON m.id = p.recipient_id
        WHERE p.kind = 'attendance'
        GROUP BY m.id
        ORDER BY points DESC, m.handle
        LIMIT 50
        """
    ).fetchall()

