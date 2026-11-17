import os
from pathlib import Path
from typing import Annotated

import psycopg
from fastapi import Depends
from psycopg.rows import dict_row


def connect():
    return psycopg.connect(
        os.environ["DATABASE_URL"],
        autocommit=True,
        row_factory=dict_row,
        connect_timeout=5,
    )


def connection():
    with connect() as db:
        yield db


Database = Annotated[psycopg.Connection, Depends(connection)]


def migrate(db):
    migrations = Path(__file__).resolve().parents[2] / "database"
    with db.transaction():
        db.execute("SELECT pg_advisory_xact_lock(614099)")
        db.execute("CREATE TABLE IF NOT EXISTS migrations (name text PRIMARY KEY)")
        applied = {row["name"] for row in db.execute("SELECT name FROM migrations")}
        for path in sorted(migrations.glob("*.sql")):
            if path.name in applied:
                continue
            db.execute(path.read_text(encoding="utf-8"))
            db.execute("INSERT INTO migrations (name) VALUES (%s)", (path.name,))


if __name__ == "__main__":
    with connect() as db:
        migrate(db)
