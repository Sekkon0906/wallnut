from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import AwareDatetime, BaseModel

from .database import Database
from .identity import CurrentAccount

router = APIRouter(prefix="/notifications", tags=["Avisos del campus"])
NotificationKind = Literal[
    "workshop_rescheduled", "workshop_cancelled", "evidence_submitted", "evidence_approved",
    "evidence_returned", "redemption_requested", "redemption_approved", "redemption_rejected",
]


class NotificationCursor(BaseModel):
    id: UUID
    created_at: AwareDatetime


class NotificationRecord(NotificationCursor):
    kind: NotificationKind
    title: str
    workshop_id: UUID | None
    course_id: UUID | None
    read_at: AwareDatetime | None


class NotificationPage(BaseModel):
    entries: list[NotificationRecord]
    unread_count: int
    next_cursor: NotificationCursor | None


def record_notification(db, account_id, event_key, kind, *, workshop_id=None, course_id=None):
    # This insert participates in the caller's workflow transaction.
    db.execute(
        """
        INSERT INTO campus_notifications (account_id, event_key, kind, workshop_id, course_id)
        VALUES (%s, %s, %s, %s, %s) ON CONFLICT (account_id, event_key) DO NOTHING
        """, (account_id, event_key, kind, workshop_id, course_id),
    )


def notify_agenda_change(db, workshop, actor_id, kind):
    db.execute(
        """
        INSERT INTO campus_notifications (account_id, event_key, kind, workshop_id)
        SELECT recipient, %(event)s, %(kind)s, %(workshop)s
        FROM (
            SELECT student_id AS recipient FROM workshop_enrollments WHERE workshop_id = %(workshop)s
            UNION SELECT %(facilitator)s::uuid
            UNION SELECT %(faculty)s::uuid
        ) recipients WHERE recipient <> %(actor)s
        ON CONFLICT (account_id, event_key) DO NOTHING
        """,
        {"event": f"agenda:{workshop['id']}:{workshop['schedule_revision'] + 1}",
         "kind": f"workshop_{kind}", "workshop": workshop["id"], "actor": actor_id,
         "facilitator": workshop["facilitator_id"], "faculty": workshop["faculty_id"]},
    )


def unread_count(db, account_id):
    return db.execute(
        "SELECT count(*) AS count FROM campus_notifications WHERE account_id = %s AND read_at IS NULL",
        (account_id,),
    ).fetchone()["count"]


@router.get("/unread-count")
def count_notifications(account: CurrentAccount, db: Database, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return {"unread_count": unread_count(db, account.id)}


@router.get("", response_model=NotificationPage)
def list_notifications(
    account: CurrentAccount, db: Database, response: Response,
    unread_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    before: AwareDatetime | None = None,
    before_id: UUID | None = None,
):
    if (before is None) != (before_id is None):
        raise HTTPException(422, "Completa la referencia de la página anterior.")
    with db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        count = unread_count(db, account.id)
        candidates = db.execute(
            """
            SELECT n.id, n.kind, n.workshop_id, n.course_id, n.created_at, n.read_at,
                   coalesce(c.title, s.title) AS title
            FROM campus_notifications n
            LEFT JOIN workshops w ON w.id = n.workshop_id
            LEFT JOIN workshop_calls c ON c.id = w.call_id
            LEFT JOIN course_sections s ON s.id = n.course_id
            WHERE n.account_id = %(account)s AND (NOT %(unread)s OR n.read_at IS NULL)
              AND (%(before)s::timestamptz IS NULL OR (n.created_at, n.id) < (%(before)s, %(before_id)s::uuid))
            ORDER BY n.created_at DESC, n.id DESC LIMIT %(limit)s
            """,
            {"account": account.id, "unread": unread_only, "before": before,
             "before_id": before_id, "limit": limit + 1},
        ).fetchall()
    entries = candidates[:limit]
    response.headers["Cache-Control"] = "private, no-store"
    return {"entries": entries, "unread_count": count,
            "next_cursor": NotificationCursor.model_validate(entries[-1]) if len(candidates) > limit else None}


@router.put("/read-through")
def read_through(cursor: NotificationCursor, account: CurrentAccount, db: Database, response: Response):
    with db.transaction():
        owned = db.execute(
            "SELECT 1 FROM campus_notifications WHERE account_id = %s AND id = %s AND created_at = %s",
            (account.id, cursor.id, cursor.created_at),
        ).fetchone()
        if not owned:
            raise HTTPException(404, "No encontramos esa referencia en tus avisos.")
        db.execute(
            """
            UPDATE campus_notifications SET read_at = clock_timestamp()
            WHERE account_id = %s AND read_at IS NULL AND (created_at, id) <= (%s, %s)
            """, (account.id, cursor.created_at, cursor.id),
        )
        count = unread_count(db, account.id)
    response.headers["Cache-Control"] = "private, no-store"
    return {"unread_count": count}


@router.put("/{notification_id}/read")
def read_notification(notification_id: UUID, account: CurrentAccount, db: Database, response: Response):
    with db.transaction():
        marked = db.execute(
            """
            UPDATE campus_notifications SET read_at = coalesce(read_at, clock_timestamp())
            WHERE id = %s AND account_id = %s RETURNING read_at
            """, (notification_id, account.id),
        ).fetchone()
        if not marked:
            raise HTTPException(404, "No encontramos ese aviso en tu cuenta.")
        count = unread_count(db, account.id)
    response.headers["Cache-Control"] = "private, no-store"
    return {**marked, "unread_count": count}
