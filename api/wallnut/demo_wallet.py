"""Reglas y cupo de ejemplo para el taller ficticio de Cálculo III."""
from uuid import UUID

from .economy import record_allocation


DEMO_ALLOCATION = UUID("4fa112f2-b0ee-4bc2-bbde-a824e3bcf5da")
DEMO_GOAL = (
    "Explica el criterio de convergencia que aplicaste y justifica el resultado "
    "de una serie trabajada en el taller."
)


def seed_workshop_economy(db, workshop_id):
    """Configura el taller sin reponer los Points consumidos ni alterar sus reglas."""
    with db.transaction():
        people = db.execute(
            """
            SELECT s.faculty_id, administrator.id AS admin_id
            FROM workshops w
            JOIN workshop_calls c ON c.id = w.call_id
            JOIN course_sections s ON s.id = c.course_id
            JOIN accounts faculty ON faculty.id = s.faculty_id
            JOIN accounts administrator ON administrator.google_subject = 'demo-admin'
            WHERE w.id = %s AND faculty.google_subject = 'demo-faculty'
              AND faculty.role = 'faculty' AND administrator.role = 'admin'
            """,
            (workshop_id,),
        ).fetchone()
        if people is None:
            return
        record_allocation(db, people["faculty_id"], people["admin_id"], 1000, DEMO_ALLOCATION)
        db.execute(
            """
            INSERT INTO workshop_economies (
                workshop_id, attendee_points, facilitator_points, goal_description,
                goal_coins, coin_cost, conversion_points
            )
            VALUES (%s, 20, 35, %s, 10, 8, 5)
            ON CONFLICT (workshop_id) DO NOTHING
            """,
            (workshop_id, DEMO_GOAL),
        )
