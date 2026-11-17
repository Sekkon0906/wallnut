from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import AwareDatetime, BaseModel, Field, StringConstraints

from .database import Database
from .identity import CurrentAccount

router = APIRouter(prefix="/campus-events", tags=["Eventos del campus"])
EVENTS = """
    SELECT e.*, a.display_name AS organizer, e.organizer_id = %(viewer)s AS mine,
           e.starts_at > clock_timestamp() AS upcoming,
           (SELECT count(*) FROM campus_event_enrollments j WHERE j.event_id = e.id) AS attendees,
           EXISTS (SELECT 1 FROM campus_event_enrollments j
                   WHERE j.event_id = e.id AND j.student_id = %(viewer)s) AS enrolled
    FROM campus_events e JOIN accounts a ON a.id = e.organizer_id
"""


class EventInput(BaseModel):
    id: UUID
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=100)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=1200)]
    category: Literal["workshop", "tournament", "campus"]
    location: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
    starts_at: AwareDatetime
    capacity: Annotated[int, Field(strict=True, ge=2, le=500)]


def get_event(db, event_id, viewer):
    result = db.execute(EVENTS + " WHERE e.id = %(event)s", {"viewer": viewer, "event": event_id}).fetchone()
    if not result:
        raise HTTPException(404, "No encontramos el evento.")
    return result


@router.get("")
def list_events(account: CurrentAccount, db: Database, response: Response,
                offset: Annotated[int, Field(ge=0)] = 0):
    response.headers["Cache-Control"] = "private, no-store"
    return db.execute(
        EVENTS + """
        WHERE e.starts_at > now() - interval '7 days'
        ORDER BY e.starts_at < now(), e.starts_at, e.id LIMIT 21 OFFSET %(offset)s
        """, {"viewer": account.id, "offset": offset},
    ).fetchall()


@router.post("", status_code=201)
def publish_event(body: EventInput, account: CurrentAccount, db: Database):
    if account.role not in {"student", "faculty", "admin"}:
        raise HTTPException(403, "Tu cuenta puede consultar los eventos del campus.")
    values = {**body.model_dump(), "organizer": account.id, "institutional": account.role != "student"}
    with db.transaction():
        db.execute(
            """
            INSERT INTO campus_events (id, organizer_id, institutional, title, description, category,
                                       location, starts_at, capacity)
            SELECT %(id)s, %(organizer)s, %(institutional)s, %(title)s, %(description)s, %(category)s,
                   %(location)s, %(starts_at)s, %(capacity)s
            WHERE %(starts_at)s > clock_timestamp()
            ON CONFLICT DO NOTHING
            """,
            values,
        )
        existing = db.execute("SELECT * FROM campus_events WHERE id = %s", (body.id,)).fetchone()
        if not existing:
            raise HTTPException(422, "Elige una fecha de inicio futura.")
        if existing["organizer_id"] != account.id or any(
            existing[key] != value for key, value in body.model_dump().items()
        ):
            raise HTTPException(409, "Este identificador ya está asociado a otro evento.")
        return get_event(db, body.id, account.id)


@router.put("/{event_id}/enrollment")
@router.delete("/{event_id}/enrollment")
def change_enrollment(event_id: UUID, request: Request, account: CurrentAccount, db: Database):
    if account.role != "student":
        raise HTTPException(403, "Solo los estudiantes pueden inscribirse.")
    with db.transaction():
        db.execute("SELECT id FROM campus_events WHERE id = %s FOR UPDATE", (event_id,)).fetchone()
        event = get_event(db, event_id, account.id)
        joining = request.method == "PUT"
        if event["enrolled"] == joining:
            return event
        if not event["upcoming"] or event["cancelled"]:
            raise HTTPException(409, "La inscripción del evento está cerrada.")
        if joining:
            if event["attendees"] >= event["capacity"]:
                raise HTTPException(409, "Ya se ocuparon todos los cupos.")
            db.execute("INSERT INTO campus_event_enrollments VALUES (%s, %s)", (event_id, account.id))
        else:
            db.execute("DELETE FROM campus_event_enrollments WHERE event_id = %s AND student_id = %s",
                       (event_id, account.id))
        return get_event(db, event_id, account.id)


@router.put("/{event_id}/cancel")
def cancel_event(event_id: UUID, account: CurrentAccount, db: Database):
    with db.transaction():
        event = get_event(db, event_id, account.id)
        if not event["mine"] and account.role != "admin":
            raise HTTPException(403, "Solo quien organiza o administra puede cancelar este evento.")
        db.execute("UPDATE campus_events SET cancelled = true WHERE id = %s", (event_id,))
        return get_event(db, event_id, account.id)
