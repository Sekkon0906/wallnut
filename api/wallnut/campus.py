from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints

from .database import Database
from .identity import Account, CurrentAccount

router = APIRouter(tags=["Campus"])
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=24)]
Email = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=254)]


class FacultyAssignment(BaseModel):
    email: Email


class EnrollmentInput(BaseModel):
    email: Email


class CourseInput(BaseModel):
    code: Identifier
    title: Label
    term: Identifier
    section: Identifier
    faculty_id: UUID


def require_admin(account: CurrentAccount):
    if account.role != "admin":
        raise HTTPException(403, "Esta acción es para administración.")
    return account


Admin = Annotated[Account, Depends(require_admin)]


def course_owner(db, course_id, account):
    course = db.execute(
        "SELECT id, faculty_id FROM course_sections WHERE id = %s", (course_id,)
    ).fetchone()
    if not course:
        raise HTTPException(404, "No encontramos el grupo.")
    if account.role != "faculty" or course["faculty_id"] != account.id:
        raise HTTPException(403, "Solo el docente asignado puede gestionar este grupo.")
    return course


@router.post("/faculty")
def assign_faculty(body: FacultyAssignment, admin: Admin, db: Database):
    faculty = db.execute(
        """
        UPDATE accounts SET role = 'faculty'
        WHERE email = %s AND role IN ('staff', 'faculty')
        RETURNING id, email, display_name, role
        """,
        (body.email.lower(),),
    ).fetchone()
    if not faculty:
        raise HTTPException(404, "El docente debe tener primero una cuenta institucional de personal.")
    return faculty


@router.get("/faculty")
def list_faculty(admin: Admin, db: Database):
    return db.execute(
        "SELECT id, email, display_name FROM accounts WHERE role = 'faculty' ORDER BY display_name, id"
    ).fetchall()


@router.post("/courses", status_code=201)
def create_course(body: CourseInput, admin: Admin, db: Database):
    course = db.execute(
        """
        INSERT INTO course_sections (code, title, term, section, faculty_id)
        SELECT %(code)s, %(title)s, %(term)s, %(section)s, id
        FROM accounts WHERE id = %(faculty_id)s AND role = 'faculty'
        ON CONFLICT (code, term, section) DO NOTHING
        RETURNING id, code, title, term, section, faculty_id
        """,
        body.model_dump(),
    ).fetchone()
    if not course:
        raise HTTPException(409, "El grupo ya existe o el docente no está habilitado.")
    return course


@router.get("/courses")
def list_courses(account: CurrentAccount, db: Database):
    return db.execute(
        """
        SELECT c.id, c.code, c.title, c.term, c.section,
               a.display_name AS faculty,
               EXISTS (SELECT 1 FROM enrollments e
                       WHERE e.course_id = c.id AND e.account_id = %(id)s) AS enrolled
        FROM course_sections c JOIN accounts a ON a.id = c.faculty_id
        WHERE %(role)s = 'admin'
           OR (%(role)s = 'faculty' AND c.faculty_id = %(id)s)
           OR EXISTS (SELECT 1 FROM enrollments e
                      WHERE e.course_id = c.id AND e.account_id = %(id)s)
        ORDER BY c.term DESC, c.code, c.section
        """,
        {"id": account.id, "role": account.role},
    ).fetchall()


@router.put("/courses/{course_id}/students")
def confirm_enrollment(course_id: UUID, body: EnrollmentInput, account: CurrentAccount,
                       db: Database):
    if account.role != "admin":
        course_owner(db, course_id, account)
    email = body.email.lower()
    enrollment = db.execute(
        """
        INSERT INTO enrollments (course_id, account_id, confirmed_by)
        SELECT c.id, a.id, %(reviewer)s
        FROM course_sections c CROSS JOIN accounts a
        WHERE c.id = %(course)s AND a.email = %(email)s AND a.role = 'student'
        ON CONFLICT (course_id, account_id) DO NOTHING
        RETURNING course_id, account_id, confirmed_by, confirmed_at
        """,
        {"course": course_id, "email": email, "reviewer": account.id},
    ).fetchone()
    if not enrollment:
        enrollment = db.execute(
            """
            SELECT e.course_id, e.account_id, e.confirmed_by, e.confirmed_at
            FROM enrollments e JOIN accounts a ON a.id = e.account_id
            WHERE e.course_id = %s AND a.email = %s
            """,
            (course_id, email),
        ).fetchone()
    if not enrollment:
        raise HTTPException(404, "No encontramos el grupo o la cuenta del estudiante.")
    return enrollment
