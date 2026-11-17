from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict

from .database import Database
from .identity import CurrentAccount
from .tournaments import tournament_event

router = APIRouter(prefix="/campus-events/{event_id}/tournament", tags=["Parejas del torneo"])


class Invitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    student_id: UUID


def doubles_event(db, event_id, account, response, *, lock=False):
    response.headers["Cache-Control"] = "private, no-store"
    if account.role != "student":
        raise HTTPException(403, "La inscripción por parejas está disponible para estudiantes.")
    event = tournament_event(db, event_id, lock=lock)
    if event["tournament_format"] != "doubles":
        raise HTTPException(404, "Este evento no usa inscripción por parejas.")
    return event


def can_form_pairs(db, event):
    if event["cancelled"]:
        return False
    return db.execute(
        """
        SELECT %s > clock_timestamp()
            AND NOT EXISTS (SELECT 1 FROM campus_tournaments WHERE event_id = %s) AS open
        """,
        (event["starts_at"], event["id"]),
    ).fetchone()["open"]


def require_open(db, event):
    if not can_form_pairs(db, event):
        raise HTTPException(409, "El registro de parejas está cerrado.")


def participant(db, event_id, student_id):
    return db.execute(
        "SELECT 1 FROM campus_event_enrollments WHERE event_id = %s AND student_id = %s",
        (event_id, student_id),
    ).fetchone() is not None


def already_paired(db, event_id, first, second):
    return db.execute(
        """
        SELECT 1 FROM tournament_pairs
        WHERE event_id = %(event)s AND accepted_at IS NOT NULL
          AND (inviter_id IN (%(first)s, %(second)s) OR invitee_id IN (%(first)s, %(second)s))
        LIMIT 1
        """,
        {"event": event_id, "first": first, "second": second},
    ).fetchone() is not None


def my_pairing(db, event, account):
    values = {"event": event["id"], "student": account.id}
    enrolled = participant(db, event["id"], account.id)
    open_registration = can_form_pairs(db, event)
    related = db.execute(
        """
        SELECT pair.id, pair.inviter_id = %(student)s AS outgoing,
               pair.accepted_at IS NOT NULL AS accepted,
               other.id AS student_id, other.display_name AS name
        FROM tournament_pairs pair
        JOIN accounts other ON other.id = CASE
            WHEN pair.inviter_id = %(student)s THEN pair.invitee_id ELSE pair.inviter_id END
        WHERE pair.event_id = %(event)s
          AND (pair.inviter_id = %(student)s OR pair.invitee_id = %(student)s)
        ORDER BY pair.created_at, pair.id
        """,
        values,
    ).fetchall()
    pair = next((row for row in related if row["accepted"]), None)
    invitations = [row for row in related if not row["accepted"]] if open_registration else []
    available = []
    if open_registration and enrolled and not pair and not any(row["outgoing"] for row in invitations):
        available = db.execute(
            """
            SELECT a.id, a.display_name AS name
            FROM campus_event_enrollments e JOIN accounts a ON a.id = e.student_id
            WHERE e.event_id = %(event)s AND a.id <> %(student)s AND a.role = 'student'
              AND NOT EXISTS (
                  SELECT 1 FROM tournament_pairs p
                  WHERE p.event_id = e.event_id AND p.accepted_at IS NOT NULL
                    AND (p.inviter_id = a.id OR p.invitee_id = a.id)
              )
            ORDER BY a.display_name, a.id
            """,
            values,
        ).fetchall()
    return {"open": open_registration, "enrolled": enrolled, "pair": pair,
            "invitations": invitations, "available": available}


@router.get("/pairing")
def read_pairing(event_id: UUID, account: CurrentAccount, db: Database, response: Response):
    with db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        event = doubles_event(db, event_id, account, response)
        return my_pairing(db, event, account)


@router.post("/pair-invitations", status_code=201)
def invite(event_id: UUID, body: Invitation, account: CurrentAccount, db: Database, response: Response):
    with db.transaction():
        event = doubles_event(db, event_id, account, response, lock=True)
        existing = db.execute(
            "SELECT event_id, inviter_id, invitee_id FROM tournament_pairs WHERE id = %s",
            (body.id,),
        ).fetchone()
        if existing:
            if (existing["event_id"], existing["inviter_id"], existing["invitee_id"]) == (
                event_id, account.id, body.student_id
            ):
                return my_pairing(db, event, account)
            raise HTTPException(409, "El identificador ya corresponde a otra invitación.")
        require_open(db, event)
        if body.student_id == account.id:
            raise HTTPException(422, "Elige a otra persona para formar pareja.")
        if not participant(db, event_id, account.id) or not participant(db, event_id, body.student_id):
            raise HTTPException(409, "Ambas personas deben estar inscritas en el torneo.")
        if already_paired(db, event_id, account.id, body.student_id):
            raise HTTPException(409, "Una de las personas ya confirmó pareja.")
        row = db.execute(
            """
            INSERT INTO tournament_pairs (id, event_id, inviter_id, invitee_id)
            VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING id
            """,
            (body.id, event_id, account.id, body.student_id),
        ).fetchone()
        if not row:
            raise HTTPException(409, "Ya existe una invitación con ese identificador o tienes un envío pendiente.")
        return my_pairing(db, event, account)


@router.put("/pair-invitations/{invitation_id}/accept")
def accept(event_id: UUID, invitation_id: UUID, account: CurrentAccount, db: Database, response: Response):
    with db.transaction():
        event = doubles_event(db, event_id, account, response, lock=True)
        invitation = db.execute(
            """
            SELECT inviter_id, accepted_at FROM tournament_pairs
            WHERE event_id = %s AND id = %s AND invitee_id = %s
            """,
            (event_id, invitation_id, account.id),
        ).fetchone()
        if not invitation:
            raise HTTPException(404, "No encontramos una invitación para tu cuenta.")
        if invitation["accepted_at"]:
            return my_pairing(db, event, account)
        require_open(db, event)
        inviter = invitation["inviter_id"]
        if already_paired(db, event_id, inviter, account.id):
            raise HTTPException(409, "Una de las personas ya confirmó pareja.")
        values = {"id": invitation_id, "event": event_id, "first": inviter, "second": account.id}
        db.execute("UPDATE tournament_pairs SET accepted_at = clock_timestamp() WHERE id = %(id)s", values)
        db.execute(
            """
            DELETE FROM tournament_pairs
            WHERE event_id = %(event)s AND accepted_at IS NULL
              AND (inviter_id IN (%(first)s, %(second)s) OR invitee_id IN (%(first)s, %(second)s))
            """,
            values,
        )
        return my_pairing(db, event, account)


@router.delete("/pair-invitations/{invitation_id}")
def remove(event_id: UUID, invitation_id: UUID, account: CurrentAccount, db: Database, response: Response):
    with db.transaction():
        event = doubles_event(db, event_id, account, response, lock=True)
        require_open(db, event)
        db.execute(
            """
            DELETE FROM tournament_pairs WHERE event_id = %s AND id = %s AND %s IN (inviter_id, invitee_id)
            """,
            (event_id, invitation_id, account.id),
        )
        return my_pairing(db, event, account)
