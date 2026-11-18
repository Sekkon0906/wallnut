from secrets import token_urlsafe
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import AwareDatetime, BaseModel, Field, StringConstraints

from .auth import Database, Member, Organizer, digest
from .points import lock_members

router = APIRouter(prefix="/activities", tags=["Actividades"])
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
Location = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class Activity(BaseModel):
    title: Title
    description: Description
    location: Location
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    reward: Annotated[int, Field(strict=True, ge=1, le=500)]


class Checkin(BaseModel):
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=20, max_length=100)]


@router.get("")
def list_activities(member: Member, db: Database):
    return db.execute(
        """
        SELECT a.id, a.title, a.description, a.location, a.starts_at, a.ends_at, a.reward,
               m.display_name AS organizer, a.organizer_id = %(member)s AS can_issue_code,
               now() BETWEEN a.starts_at AND a.ends_at AS in_progress,
               p.id IS NOT NULL AS attended
        FROM activities a
        JOIN members m ON m.id = a.organizer_id
        LEFT JOIN point_movements p ON p.activity_id = a.id AND p.recipient_id = %(member)s
        WHERE a.ends_at > now()
        ORDER BY a.starts_at, a.id
        LIMIT 50
        """,
        {"member": member["id"]},
    ).fetchall()


@router.post("", status_code=201)
def publish_activity(body: Activity, organizer: Organizer, db: Database):
    if body.ends_at <= body.starts_at:
        raise HTTPException(422, "La hora de cierre debe ser posterior a la de inicio.")
    return db.execute(
        """
        INSERT INTO activities (organizer_id, title, description, location, starts_at, ends_at, reward)
        VALUES (%(owner)s, %(title)s, %(description)s, %(location)s, %(starts_at)s, %(ends_at)s, %(reward)s)
        RETURNING id
        """,
        {"owner": organizer["id"], **body.model_dump()},
    ).fetchone()


@router.post("/{activity_id}/code")
def issue_code(activity_id: UUID, organizer: Organizer, db: Database):
    code = token_urlsafe(24)
    activity = db.execute(
        """
        UPDATE activities
        SET checkin_hash = %s, checkin_expires_at = least(ends_at, now() + interval '2 minutes')
        WHERE id = %s AND organizer_id = %s AND starts_at <= now() AND ends_at > now()
        RETURNING checkin_expires_at AS expires_at
        """,
        (digest(code), activity_id, organizer["id"]),
    ).fetchone()
    if not activity:
        raise HTTPException(409, "El QR está disponible para el organizador durante su actividad.")
    return {"code": code, "expires_at": activity["expires_at"]}


@router.post("/{activity_id}/attendance")
def record_attendance(activity_id: UUID, body: Checkin, member: Member, db: Database):
    if member["role"] != "student":
        raise HTTPException(403, "El registro de asistencia es para estudiantes.")
    member_id = member["id"]
    with db.transaction():
        lock_members(db, [member_id])
        previous = db.execute(
            "SELECT id, points FROM point_movements WHERE activity_id = %s AND recipient_id = %s",
            (activity_id, member_id),
        ).fetchone()
        if previous:
            return {**previous, "already_recorded": True}

        activity = db.execute(
            """
            SELECT reward FROM activities
            WHERE id = %s AND checkin_hash = %s
              AND starts_at <= clock_timestamp() AND checkin_expires_at > clock_timestamp()
            FOR SHARE
            """,
            (activity_id, digest(body.code)),
        ).fetchone()
        if not activity:
            raise HTTPException(409, "El código venció o no corresponde a esta actividad.")
        movement = db.execute(
            """
            INSERT INTO point_movements (kind, recipient_id, activity_id, points)
            VALUES ('attendance', %s, %s, %s) RETURNING id, points
            """,
            (member_id, activity_id, activity["reward"]),
        ).fetchone()
        return {**movement, "already_recorded": False}

