from datetime import timedelta
from hashlib import sha256
from secrets import choice
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from pydantic import AwareDatetime, BaseModel, Field, StringConstraints, model_validator

from .community import load_call
from .database import Database
from .identity import CurrentAccount


router = APIRouter(tags=["Talleres"])
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8
CODE_DURATION = timedelta(minutes=5)


class WorkshopSchedule(BaseModel):
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    location: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160,
                                               pattern=r"^[^\x00]*$")]
    capacity: Annotated[int, Field(strict=True, ge=1, le=300)]

    @model_validator(mode="after")
    def validate_dates(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("La hora de finalización debe ser posterior a la de inicio.")
        return self


class AttendanceInput(BaseModel):
    code: Annotated[
        str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=CODE_LENGTH,
                               max_length=CODE_LENGTH)
    ]


class WorkshopParticipant(BaseModel):
    student_id: UUID
    display_name: str
    checked_in_at: AwareDatetime | None
    evidence_status: Literal["submitted", "returned", "approved"] | None


def load_workshop(db, workshop_id, *, exclusive_lock=False):
    lock = "FOR UPDATE OF w" if exclusive_lock else "FOR SHARE OF w"
    row = db.execute(
        f"""
        SELECT w.id, w.starts_at, w.ends_at, w.location, w.capacity, w.facilitator_id,
               w.cancelled_at, w.schedule_revision,
               w.attendance_code_hash, w.attendance_code_expires_at, s.faculty_id
        FROM workshops w
        JOIN workshop_calls c ON c.id = w.call_id
        JOIN course_sections s ON s.id = c.course_id
        WHERE w.id = %s {lock}
        """,
        (workshop_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "No encontramos el taller.")
    return row


def database_time(db):
    return db.execute("SELECT clock_timestamp() AS current_time").fetchone()["current_time"]


def is_facilitator(workshop, account):
    return account.role == "student" and workshop["facilitator_id"] == account.id


def is_assigned_faculty(workshop, account):
    return account.role == "faculty" and workshop["faculty_id"] == account.id


def require_active_workshop(workshop):
    if workshop["cancelled_at"] is not None:
        raise HTTPException(409, "Este taller fue cancelado.")


def code_hash(code: str) -> bytes:
    return sha256(code.encode("utf-8")).digest()


@router.get("/workshops")
def list_workshops(account: CurrentAccount, db: Database, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return db.execute(
        """
        SELECT w.id, w.call_id, c.title, s.title AS course,
               a.display_name AS facilitator_name, w.starts_at, w.ends_at, w.location, w.capacity,
               w.cancelled_at, w.schedule_revision,
               CASE WHEN ch.kind = 'rescheduled' THEN (ch.previous_schedule->>'starts_at')::timestamptz
               END AS previous_starts_at,
               ch.kind AS schedule_change, ch.reason AS schedule_notice,
               (SELECT count(*) FROM workshop_enrollments e
                WHERE e.workshop_id = w.id) AS enrolled_count,
               EXISTS (SELECT 1 FROM workshop_enrollments e
                       WHERE e.workshop_id = w.id AND e.student_id = %(account)s) AS enrolled,
               EXISTS (SELECT 1 FROM workshop_attendance t
                       WHERE t.workshop_id = w.id AND t.student_id = %(account)s) AS attended,
               (%(faculty)s AND s.faculty_id = %(account)s) AS can_manage,
               ((%(faculty)s AND s.faculty_id = %(account)s) OR %(admin)s) AS can_cancel,
               ((%(faculty)s AND s.faculty_id = %(account)s)
                OR (%(student)s AND w.facilitator_id = %(account)s)) AS can_issue_code,
               (%(student)s AND w.facilitator_id = %(account)s) AS is_facilitator
        FROM workshops w
        JOIN workshop_calls c ON c.id = w.call_id
        JOIN course_sections s ON s.id = c.course_id
        JOIN accounts a ON a.id = w.facilitator_id
        LEFT JOIN workshop_agenda_changes ch ON ch.workshop_id = w.id AND ch.revision = w.schedule_revision
        ORDER BY w.cancelled_at IS NOT NULL OR w.ends_at <= now(), w.starts_at, w.id
        """,
        {"account": account.id, "faculty": account.role == "faculty",
         "student": account.role == "student", "admin": account.role == "admin"},
    ).fetchall()


@router.get("/workshops/{workshop_id}/participants", response_model=list[WorkshopParticipant])
def list_workshop_participants(workshop_id: UUID, account: CurrentAccount, db: Database, response: Response):
    with db.transaction():
        workshop = load_workshop(db, workshop_id)
        if not is_assigned_faculty(workshop, account):
            raise HTTPException(403, "Solo el docente asignado puede consultar la lista de inscritos.")
        participants = db.execute(
            """
            SELECT e.student_id, a.display_name, t.checked_in_at, v.status AS evidence_status
            FROM workshop_enrollments e
            JOIN accounts a ON a.id = e.student_id
            LEFT JOIN workshop_attendance t USING (workshop_id, student_id)
            LEFT JOIN workshop_evidence v ON (v.workshop_id, v.student_id) = (e.workshop_id, e.student_id)
            WHERE e.workshop_id = %s
            ORDER BY lower(a.display_name), a.display_name, e.student_id
            """,
            (workshop_id,),
        ).fetchall()
    response.headers["Cache-Control"] = "private, no-store"
    return participants


@router.post("/workshop-calls/{call_id}/workshop", status_code=201)
def schedule_workshop(call_id: UUID, body: WorkshopSchedule, account: CurrentAccount, db: Database):
    with db.transaction():
        call = load_call(db, call_id, lock=True)
        context = db.execute(
            """
            SELECT s.faculty_id, a.student_id AS facilitator_id,
                   EXISTS (SELECT 1 FROM workshops w WHERE w.call_id = %(call)s) AS scheduled
            FROM course_sections s
            LEFT JOIN facilitator_applications a ON a.call_id = %(call)s AND a.status = 'approved'
            WHERE s.id = %(course)s
            """,
            {"call": call_id, "course": call["course_id"]},
        ).fetchone()
        if not (is_assigned_faculty(context, account) or is_facilitator(context, account)):
            raise HTTPException(403, "Solo el docente o el tallerista aprobado pueden agendar este taller.")
        if not context["facilitator_id"]:
            raise HTTPException(409, "Primero selecciona un tallerista.")
        if context["scheduled"]:
            raise HTTPException(409, "El taller ya está agendado.")
        if body.starts_at <= database_time(db):
            raise HTTPException(409, "Elige una fecha de inicio en el futuro.")
        return db.execute(
            """
            INSERT INTO workshops (call_id, facilitator_id, starts_at, ends_at, location, capacity)
            VALUES (%(call)s, %(facilitator)s, %(starts_at)s, %(ends_at)s, %(location)s, %(capacity)s)
            RETURNING id, call_id, starts_at, ends_at, location, capacity
            """,
            {**body.model_dump(), "call": call_id, "facilitator": context["facilitator_id"]},
        ).fetchone()


@router.put("/workshops/{workshop_id}/enrollment")
def enroll_in_workshop(workshop_id: UUID, account: CurrentAccount, db: Database, response: Response):
    if account.role != "student":
        raise HTTPException(403, "Las inscripciones son para estudiantes.")
    with db.transaction():
        workshop = load_workshop(db, workshop_id, exclusive_lock=True)
        require_active_workshop(workshop)
        if is_facilitator(workshop, account):
            raise HTTPException(403, "Ya participas en este taller como tallerista.")
        enrollment = db.execute(
            """
            SELECT enrolled_at FROM workshop_enrollments
            WHERE workshop_id = %s AND student_id = %s
            """,
            (workshop_id, account.id),
        ).fetchone()
        if enrollment:
            return enrollment
        if database_time(db) >= workshop["starts_at"]:
            raise HTTPException(409, "Las inscripciones cerraron al iniciar el taller.")
        occupied = db.execute(
            "SELECT count(*) AS occupied FROM workshop_enrollments WHERE workshop_id = %s",
            (workshop_id,),
        ).fetchone()["occupied"]
        if occupied >= workshop["capacity"]:
            raise HTTPException(409, "El taller ya no tiene cupos disponibles.")
        response.status_code = 201
        return db.execute(
            """
            INSERT INTO workshop_enrollments (workshop_id, student_id)
            VALUES (%s, %s) RETURNING enrolled_at
            """,
            (workshop_id, account.id),
        ).fetchone()


@router.delete("/workshops/{workshop_id}/enrollment", status_code=204)
def cancel_enrollment(workshop_id: UUID, account: CurrentAccount, db: Database):
    if account.role != "student":
        raise HTTPException(403, "Las inscripciones son para estudiantes.")
    with db.transaction():
        workshop = load_workshop(db, workshop_id, exclusive_lock=True)
        require_active_workshop(workshop)
        if database_time(db) >= workshop["starts_at"]:
            raise HTTPException(409, "La inscripción solo se puede cancelar antes del taller.")
        db.execute(
            "DELETE FROM workshop_enrollments WHERE workshop_id = %s AND student_id = %s",
            (workshop_id, account.id),
        )
    return Response(status_code=204)


@router.post("/workshops/{workshop_id}/attendance-code")
def issue_attendance_code(workshop_id: UUID, account: CurrentAccount, db: Database,
                          response: Response):
    with db.transaction():
        workshop = load_workshop(db, workshop_id, exclusive_lock=True)
        if not (is_assigned_faculty(workshop, account) or is_facilitator(workshop, account)):
            raise HTTPException(403, "Solo el docente o el tallerista pueden generar el código.")
        require_active_workshop(workshop)
        now = database_time(db)
        if not workshop["starts_at"] <= now < workshop["ends_at"]:
            raise HTTPException(409, "El código se genera durante el horario del taller.")
        while True:
            code = "".join(choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            digest = code_hash(code)
            if digest != workshop["attendance_code_hash"]:
                break
        expires_at = min(now + CODE_DURATION, workshop["ends_at"])
        db.execute(
            """
            UPDATE workshops SET attendance_code_hash = %s, attendance_code_expires_at = %s
            WHERE id = %s
            """,
            (digest, expires_at, workshop_id),
        )
    response.headers["Cache-Control"] = "no-store"
    return {
        "code": code,
        "qr_value": f"wallnut:attendance:{workshop_id}:{code}",
        "expires_at": expires_at,
    }


@router.post("/workshops/{workshop_id}/attendance")
def check_in(workshop_id: UUID, body: AttendanceInput, account: CurrentAccount, db: Database):
    if account.role != "student":
        raise HTTPException(403, "El registro de asistencia es para estudiantes.")
    with db.transaction():
        workshop = load_workshop(db, workshop_id)
        require_active_workshop(workshop)
        enrollment = db.execute(
            """
            SELECT t.checked_in_at FROM workshop_enrollments e
            LEFT JOIN workshop_attendance t USING (workshop_id, student_id)
            WHERE e.workshop_id = %s AND e.student_id = %s
            """,
            (workshop_id, account.id),
        ).fetchone()
        if not enrollment:
            raise HTTPException(403, "Inscríbete antes de registrar tu asistencia.")
        if enrollment["checked_in_at"]:
            return {**enrollment, "already_recorded": True}

        now = database_time(db)
        if not workshop["starts_at"] <= now < workshop["ends_at"]:
            raise HTTPException(409, "La asistencia se registra durante el horario del taller.")
        if (
            workshop["attendance_code_expires_at"] is None
            or workshop["attendance_code_expires_at"] <= now
            or workshop["attendance_code_hash"] != code_hash(body.code)
        ):
            raise HTTPException(400, "El código es inválido o venció. Pide el código actual.")

        checked_in = db.execute(
            """
            INSERT INTO workshop_attendance (workshop_id, student_id, checked_in_at)
            VALUES (%s, %s, %s) ON CONFLICT (workshop_id, student_id) DO NOTHING
            RETURNING checked_in_at
            """,
            (workshop_id, account.id, now),
        ).fetchone()
        if checked_in:
            return {**checked_in, "already_recorded": False}
        existing = db.execute(
            """
            SELECT checked_in_at FROM workshop_attendance
            WHERE workshop_id = %s AND student_id = %s
            """,
            (workshop_id, account.id),
        ).fetchone()
        return {**existing, "already_recorded": True}
