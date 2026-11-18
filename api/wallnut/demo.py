import argparse
from datetime import datetime, timedelta, timezone
from uuid import UUID

from .auth import password_hash
from .db import connect, migrate

PASSWORD = "Wallnut-Demo-26"
ORGANIZER_ID = UUID("4dfef573-1a4e-43f7-8b82-9dffdc49c873")
ACTIVITIES = [
    (UUID("5315ee07-0697-4469-92ca-a26e1a4cfc6c"), "Exploración del campus",
     "Recorrido participativo por los espacios que puedes usar durante el semestre.",
     "Plazoleta central", -1, 2, 30),
    (UUID("4fdc4146-a3cc-4f1c-a32a-f38ad241b804"), "Laboratorio de ideas",
     "Sesión de prototipado para propuestas de la comunidad universitaria.",
     "Sala de innovación", 24, 26, 45),
    (UUID("7a6f11b4-c82a-480a-a87a-57fb1d52fd04"), "Encuentro de lectura",
     "Conversación abierta con estudiantes alrededor de una lectura corta.",
     "Biblioteca", 48, 50, 20),
]


def seed(connection):
    now = datetime.now(timezone.utc)
    hashed = password_hash.hash(PASSWORD)
    with connection.transaction():
        connection.execute(
            """
            INSERT INTO members (id, email, handle, display_name, password_hash, role)
            VALUES (%s, 'organiza@example.test', 'organiza', 'Equipo Campus', %s, 'organizer')
            ON CONFLICT (id) DO NOTHING
            """,
            (ORGANIZER_ID, hashed),
        )
        for handle, name in (("vale", "Valentina"), ("nico", "Nicolás")):
            connection.execute(
                """
                INSERT INTO members (email, handle, display_name, password_hash, role)
                VALUES (%s, %s, %s, %s, 'student') ON CONFLICT (email) DO NOTHING
                """,
                (f"{handle}@example.test", handle, name, hashed),
            )
        for activity_id, title, description, location, start, end, reward in ACTIVITIES:
            connection.execute(
                """
                INSERT INTO activities (id, organizer_id, title, description, location,
                                        starts_at, ends_at, reward)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    starts_at = EXCLUDED.starts_at, ends_at = EXCLUDED.ends_at,
                    checkin_hash = NULL, checkin_expires_at = NULL
                """,
                (activity_id, ORGANIZER_ID, title, description, location,
                 now + timedelta(hours=start), now + timedelta(hours=end), reward),
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga cuentas ficticias en una base de desarrollo.")
    parser.add_argument("--local-demo", action="store_true", required=True)
    parser.parse_args()
    with connect() as connection:
        migrate(connection)
        seed(connection)
    print("Cuentas demo listas. Consulta el README para iniciar sesión.")

