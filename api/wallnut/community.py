from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, HttpUrl, StringConstraints

from .campus import Label, course_owner
from .database import Database
from .identity import CurrentAccount

router = APIRouter(prefix="/workshop-calls", tags=["Comunidad"])
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=1800)]
CALLS = """
    SELECT c.id, c.course_id, c.title, c.description, c.created_at, s.title AS course,
           a.display_name AS faculty,
           NOT EXISTS (SELECT 1 FROM facilitator_applications
                       WHERE call_id = c.id AND status = 'approved') AS open,
           s.faculty_id = %(student)s AND %(faculty)s AS can_manage,
           EXISTS (
               SELECT 1 FROM facilitator_applications selected
               WHERE selected.call_id = c.id AND selected.status = 'approved'
                 AND (selected.student_id = %(student)s
                      OR (s.faculty_id = %(student)s AND %(faculty)s))
           ) AND NOT EXISTS (
               SELECT 1 FROM workshops scheduled WHERE scheduled.call_id = c.id
           ) AS can_schedule,
           (SELECT status FROM facilitator_applications
            WHERE call_id = c.id AND student_id = %(student)s) AS my_application
    FROM workshop_calls c
    JOIN course_sections s ON s.id = c.course_id
    JOIN accounts a ON a.id = s.faculty_id
"""


class WorkshopCall(BaseModel):
    course_id: UUID
    title: Label
    description: Description


class Application(BaseModel):
    proposal: Description
    evidence_url: HttpUrl | None = None


def load_call(db, call_id, *, lock=False):
    query = "SELECT id, course_id FROM workshop_calls WHERE id = %s"
    if lock:
        query += " FOR UPDATE"
    call = db.execute(query, (call_id,)).fetchone()
    if not call:
        raise HTTPException(404, "No encontramos la convocatoria.")
    return call


@router.get("")
def list_calls(account: CurrentAccount, db: Database,
               limit: Annotated[int, Query(ge=1, le=50)] = 25,
               offset: Annotated[int, Query(ge=0)] = 0):
    return db.execute(
        CALLS + """
        ORDER BY c.created_at DESC, c.id DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {"student": account.id, "faculty": account.role == "faculty",
         "limit": limit, "offset": offset},
    ).fetchall()


@router.get("/{call_id}")
def read_call(call_id: UUID, account: CurrentAccount, db: Database, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    call = db.execute(CALLS + " WHERE c.id = %(id)s", {
        "id": call_id, "student": account.id, "faculty": account.role == "faculty",
    }).fetchone()
    if not call:
        raise HTTPException(404, "No encontramos la convocatoria.")
    return call


@router.post("", status_code=201)
def publish_call(body: WorkshopCall, account: CurrentAccount, db: Database):
    course_owner(db, body.course_id, account)
    return db.execute(
        """
        INSERT INTO workshop_calls (course_id, title, description)
        VALUES (%(course_id)s, %(title)s, %(description)s)
        RETURNING id, course_id, title, description, created_at
        """,
        body.model_dump(),
    ).fetchone()


@router.post("/{call_id}/applications", status_code=201)
def apply_for_call(call_id: UUID, body: Application, account: CurrentAccount, db: Database):
    if account.role != "student":
        raise HTTPException(403, "Las postulaciones son para estudiantes.")
    with db.transaction():
        load_call(db, call_id, lock=True)
        winner = db.execute(
            "SELECT id FROM facilitator_applications WHERE call_id = %s AND status = 'approved'",
            (call_id,),
        ).fetchone()
        if winner:
            raise HTTPException(409, "La convocatoria ya tiene tallerista.")
        application = db.execute(
            """
            INSERT INTO facilitator_applications (call_id, student_id, proposal, evidence_url)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (call_id, student_id) DO NOTHING
            RETURNING id, call_id, status, submitted_at
            """,
            (call_id, account.id, body.proposal, str(body.evidence_url) if body.evidence_url else None),
        ).fetchone()
        if not application:
            raise HTTPException(409, "Ya tienes una postulación a esta convocatoria.")
        return application


@router.get("/{call_id}/applications")
def list_applications(call_id: UUID, account: CurrentAccount, db: Database):
    call = load_call(db, call_id)
    course_owner(db, call["course_id"], account)
    return db.execute(
        """
        SELECT p.id, p.proposal, p.evidence_url, p.status, p.submitted_at,
               a.id AS student_id, a.display_name
        FROM facilitator_applications p JOIN accounts a ON a.id = p.student_id
        WHERE p.call_id = %s ORDER BY p.submitted_at, p.id
        """,
        (call_id,),
    ).fetchall()


@router.put("/{call_id}/applications/{application_id}/approval")
def approve_application(call_id: UUID, application_id: UUID, account: CurrentAccount,
                        db: Database):
    with db.transaction():
        call = load_call(db, call_id, lock=True)
        course_owner(db, call["course_id"], account)
        application = db.execute(
            """
            SELECT id, call_id, student_id, status FROM facilitator_applications
            WHERE id = %s AND call_id = %s
            """,
            (application_id, call_id),
        ).fetchone()
        if not application:
            raise HTTPException(404, "No encontramos esa postulación.")
        if application["status"] == "approved":
            return application
        if application["status"] == "not_selected":
            raise HTTPException(409, "La convocatoria ya tiene tallerista.")
        db.execute(
            """
            UPDATE facilitator_applications
            SET status = CASE WHEN id = %s THEN 'approved' ELSE 'not_selected' END,
                reviewed_at = now()
            WHERE call_id = %s AND status = 'pending'
            """,
            (application_id, call_id),
        )
        return {**application, "status": "approved"}
