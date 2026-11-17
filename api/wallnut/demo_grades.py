"""Configuración de notas y matrículas ficticias para la demostración local."""


def seed_grade_redemption(db, workshop_id):
    """Prepara Cálculo III sin modificar reglas ni notas que ya existan."""
    with db.transaction():
        group = db.execute(
            """
            SELECT s.id AS course_id, s.faculty_id, student.id AS student_id
            FROM workshops w
            JOIN workshop_calls c ON c.id = w.call_id
            JOIN course_sections s ON s.id = c.course_id
            JOIN accounts faculty ON faculty.id = s.faculty_id
            JOIN accounts student ON student.google_subject = 'demo-student'
            WHERE w.id = %s AND faculty.google_subject = 'demo-faculty'
              AND faculty.role = 'faculty' AND student.role = 'student'
              AND s.code = 'MAT303' AND s.term = 'PILOTO' AND s.section = '01'
            """,
            (workshop_id,),
        ).fetchone()
        if group is None:
            return

        db.execute(
            """
            INSERT INTO enrollments (course_id, account_id, confirmed_by)
            VALUES (%(course_id)s, %(student_id)s, %(faculty_id)s)
            ON CONFLICT (course_id, account_id) DO NOTHING
            """,
            group,
        )
        created_rule = db.execute(
            """
            INSERT INTO grade_redemption_rules (
                course_id, assessment, points_per_step, step_milli, max_bonus_milli,
                minimum_grade_milli
            )
            VALUES (%(course_id)s, 'Corte de práctica', 10, 100, 200, NULL)
            ON CONFLICT (course_id) DO NOTHING
            RETURNING course_id
            """,
            group,
        ).fetchone()
        if created_rule:
            db.execute(
                """
                INSERT INTO grade_redemption_sources (course_id, source_course_id)
                VALUES (%(course_id)s, %(course_id)s)
                """,
                group,
            )

        db.execute(
            """
            INSERT INTO simulated_grades (course_id, student_id, base_grade_milli, recorded_by)
            VALUES (%(course_id)s, %(student_id)s, 3700, %(faculty_id)s)
            ON CONFLICT (course_id, student_id) DO NOTHING
            """,
            group,
        )
