"""Datos ficticios para la demostración local."""
import os

import uvicorn
from psycopg.conninfo import conninfo_to_dict

from .database import connect, migrate
from .demo_grades import seed_grade_redemption
from .demo_wallet import seed_workshop_economy
from .identity import STAFF_DOMAIN, STUDENT_DOMAIN
from .main import create_app

DEMO_PEOPLE = {
    "demo-student": ("maria.piloto", STUDENT_DOMAIN, "María Piloto", "student"),
    "demo-second-student": ("mateo.piloto", STUDENT_DOMAIN, "Mateo Piloto", "student"),
    "demo-faculty": ("elena.piloto", STAFF_DOMAIN, "Elena Piloto", "faculty"),
    "demo-admin": ("campus.piloto", STAFF_DOMAIN, "Equipo Campus", "admin"),
}
ACTIVE_WORKSHOP = "Taller de series y convergencia"


def simulated_identity(credential):
    person = DEMO_PEOPLE.get(credential)
    if not person:
        return {}
    name, domain, title, _ = person
    return {
        "sub": credential, "email": f"{name}@{domain}", "name": title,
        "email_verified": True, "hd": domain,
    }


def seed_demo(db):
    with db.transaction():
        db.execute("SELECT pg_advisory_xact_lock(614101)")
        for subject, (name, domain, title, role) in DEMO_PEOPLE.items():
            db.execute(
                """
                INSERT INTO accounts (google_subject, email, display_name, role)
                VALUES (%s, %s, %s, %s) ON CONFLICT (google_subject) DO NOTHING
                """,
                (subject, f"{name}@{domain}", title, role),
            )
        for code, title in (("MAT303", "Cálculo III"), ("IDS101", "Diseño e innovación")):
            db.execute(
                """
                INSERT INTO course_sections (code, title, term, section, faculty_id)
                SELECT %s, %s, 'PILOTO', '01', id
                FROM accounts WHERE google_subject = 'demo-faculty'
                ON CONFLICT (code, term, section) DO NOTHING
                """,
                (code, title),
            )
        for code, title, description in (
            ("MAT303", "Se busca tallerista para Cálculo III",
             "Prepara una sesión de ejercicios sobre series y convergencia. "
             "Describe cómo explicarías el tema a estudiantes que quieren reforzar el corte."),
            ("IDS101", "Guía una sesión de prototipado",
             "Buscamos a alguien que pueda acompañar un taller de prototipos de papel. "
             "Incluye una dinámica que el grupo pueda completar en una hora."),
        ):
            db.execute(
                """
                INSERT INTO workshop_calls (course_id, title, description)
                SELECT c.id, %(title)s, %(description)s FROM course_sections c
                WHERE c.code = %(code)s AND c.term = 'PILOTO'
                  AND NOT EXISTS (SELECT 1 FROM workshop_calls w
                                  WHERE w.course_id = c.id AND w.title = %(title)s)
                """,
                {"code": code, "title": title, "description": description},
            )
        seed_active_workshop(db)


def seed_active_workshop(db):
    # Cada arranque usa el taller activo. Al cerrarse se conserva su historial.
    active = db.execute(
        """
        SELECT w.id
        FROM workshops w
        JOIN workshop_calls c ON c.id = w.call_id
        JOIN course_sections s ON s.id = c.course_id
        WHERE s.code = 'MAT303' AND s.term = 'PILOTO' AND s.section = '01'
          AND c.title = %s AND now() >= w.starts_at AND now() < w.ends_at
        """,
        (ACTIVE_WORKSHOP,),
    ).fetchone()
    if active:
        seed_workshop_economy(db, active["id"])
        seed_grade_redemption(db, active["id"])
        return

    call = db.execute(
        """
        INSERT INTO workshop_calls (course_id, title, description)
        SELECT id, %s, 'Practica los criterios de convergencia con ejercicios guiados.'
        FROM course_sections WHERE code = 'MAT303' AND term = 'PILOTO' AND section = '01'
        RETURNING id
        """,
        (ACTIVE_WORKSHOP,),
    ).fetchone()
    facilitator = db.execute(
        """
        INSERT INTO facilitator_applications (call_id, student_id, proposal, status, reviewed_at)
        SELECT %s, id, 'Explicar series y acompañar la resolución de ejercicios.', 'approved', now()
        FROM accounts WHERE google_subject = 'demo-second-student'
        RETURNING student_id
        """,
        (call["id"],),
    ).fetchone()
    workshop = db.execute(
        """
        INSERT INTO workshops (call_id, facilitator_id, starts_at, ends_at, location, capacity)
        VALUES (%s, %s, now() - interval '10 minutes', now() + interval '2 hours', 'Aula 204', 24)
        RETURNING id
        """,
        (call["id"], facilitator["student_id"]),
    ).fetchone()
    db.execute(
        """
        INSERT INTO workshop_enrollments (workshop_id, student_id)
        SELECT %s, id FROM accounts WHERE google_subject = 'demo-student'
        """,
        (workshop["id"],),
    )
    seed_workshop_economy(db, workshop["id"])
    seed_grade_redemption(db, workshop["id"])


def main():
    if conninfo_to_dict(os.environ["DATABASE_URL"]).get("dbname") != "wallnut_demo":
        raise SystemExit("La demostración requiere una base de datos llamada wallnut_demo.")
    with connect() as db:
        migrate(db)
        seed_demo(db)
    uvicorn.run(create_app(simulated_identity), host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
