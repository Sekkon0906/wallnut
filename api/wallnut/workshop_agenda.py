from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .database import Database
from .identity import CurrentAccount
from .workshops import (
    WorkshopSchedule, database_time, is_assigned_faculty, is_facilitator,
    load_workshop, require_active_workshop,
)

router = APIRouter(tags=["Agenda de talleres"])


class AgendaChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    revision: Annotated[int, Field(strict=True, ge=1)]
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=280,
                                             pattern=r"^[^\x00]*$")]


class Reschedule(AgendaChange, WorkshopSchedule):
    kind: Literal["rescheduled"]


class Cancellation(AgendaChange):
    kind: Literal["cancelled"]


def authorized(change, workshop, account):
    if is_assigned_faculty(workshop, account):
        return True
    if isinstance(change, Reschedule):
        return is_facilitator(workshop, account)
    return account.role == "admin"


def reschedule(db, workshop, change, now):
    if change.starts_at <= now:
        raise HTTPException(409, "Elige una nueva fecha de inicio en el futuro.")
    if all(getattr(change, field) == workshop[field] for field in ("starts_at", "ends_at", "location", "capacity")):
        raise HTTPException(422, "Modifica el horario, el lugar o los cupos para guardar un cambio.")
    occupied = db.execute(
        "SELECT count(*) AS total FROM workshop_enrollments WHERE workshop_id = %s", (workshop["id"],)
    ).fetchone()["total"]
    if change.capacity < occupied:
        raise HTTPException(409, f"Hay {occupied} inscripciones confirmadas. Conserva al menos esos cupos.")

    db.execute(
        """
        UPDATE workshops SET starts_at = %(starts_at)s, ends_at = %(ends_at)s,
            location = %(location)s, capacity = %(capacity)s, schedule_revision = schedule_revision + 1,
            attendance_code_hash = NULL, attendance_code_expires_at = NULL
        WHERE id = %(workshop)s
        """,
        {**change.model_dump(), "workshop": workshop["id"]},
    )


@router.put("/workshops/{workshop_id}/agenda", status_code=204)
def change_agenda(workshop_id: UUID, change: Annotated[Reschedule | Cancellation, Body(discriminator="kind")],
                  account: CurrentAccount, db: Database):
    with db.transaction():
        workshop = load_workshop(db, workshop_id, exclusive_lock=True)
        if not authorized(change, workshop, account):
            raise HTTPException(403, "Tu cuenta no puede realizar ese cambio en la agenda.")
        payload = change.model_dump(mode="json")
        previous = db.execute(
            """
            SELECT actor_id, payload FROM workshop_agenda_changes
            WHERE workshop_id = %s AND request_id = %s
            """,
            (workshop_id, change.request_id),
        ).fetchone()
        if previous:
            if previous["actor_id"] != account.id or previous["payload"] != payload:
                raise HTTPException(409, "Ese identificador ya está asociado a otro cambio de agenda.")
            return
        require_active_workshop(workshop)
        if workshop["schedule_revision"] != change.revision:
            raise HTTPException(409, "La agenda cambió. Cierra este formulario y vuelve a abrir el taller.")
        now = database_time(db)
        if now >= workshop["starts_at"]:
            raise HTTPException(409, "El taller solo se puede reprogramar o cancelar antes de que empiece.")
        db.execute(
            """
            INSERT INTO workshop_agenda_changes (
                workshop_id, revision, request_id, actor_id, kind, reason, previous_schedule, payload, changed_at
            )
            SELECT id, schedule_revision + 1, %s, %s, %s, %s,
                jsonb_build_object('starts_at', starts_at, 'ends_at', ends_at, 'location', location, 'capacity', capacity),
                %s, %s
            FROM workshops WHERE id = %s
            """,
            (change.request_id, account.id, change.kind, change.reason, Jsonb(payload), now, workshop_id),
        )
        if isinstance(change, Reschedule):
            reschedule(db, workshop, change, now)
        else:
            db.execute(
                """
                UPDATE workshops SET cancelled_at = %s, schedule_revision = schedule_revision + 1,
                    attendance_code_hash = NULL, attendance_code_expires_at = NULL
                WHERE id = %s
                """,
                (now, workshop_id),
            )
