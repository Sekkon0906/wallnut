import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


def connect():
    return psycopg.connect(
        os.environ["DATABASE_URL"],
        row_factory=dict_row,
        autocommit=True,
        connect_timeout=5,
    )


def database():
    with connect() as connection:
        yield connection


def migrate(connection):
    directory = Path(__file__).resolve().parents[2] / "database"
    with connection.transaction():
        connection.execute("SELECT pg_advisory_xact_lock(284671)")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (filename text PRIMARY KEY)
        """)
        applied = {
            row["filename"]
            for row in connection.execute("SELECT filename FROM schema_migrations")
        }
        for migration in sorted(directory.glob("*.sql")):
            if migration.name not in applied:
                connection.execute(migration.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations VALUES (%s)", (migration.name,)
                )


if __name__ == "__main__":
    with connect() as connection:
        migrate(connection)

