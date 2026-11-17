import os
from pathlib import Path
from typing import Annotated

import psycopg
from fastapi import Depends
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row


def connection_string():
    if url := os.environ.get("DATABASE_URL"):
        return url
    return make_conninfo(dbname=os.environ["PGDATABASE"])


def connect():
    return psycopg.connect(
        connection_string(),
        autocommit=True,
        row_factory=dict_row,
        connect_timeout=5,
    )


def connection():
    with connect() as db:
        yield db


Database = Annotated[psycopg.Connection, Depends(connection)]


def migration_files():
    migrations = Path(__file__).resolve().parents[2] / "database"
    return sorted(migrations.glob("*.sql"))


def applied_migrations(db):
    if db.execute("SELECT to_regclass('migrations') AS name").fetchone()["name"] is None:
        return set()
    return {row["name"] for row in db.execute("SELECT name FROM migrations")}


def pending_migrations(db):
    applied = applied_migrations(db)
    return [path for path in migration_files() if path.name not in applied]


def migrate(db):
    with db.transaction():
        db.execute("SELECT pg_advisory_xact_lock(614099)")
        db.execute("CREATE TABLE IF NOT EXISTS migrations (name text PRIMARY KEY)")
        for path in pending_migrations(db):
            db.execute(path.read_text(encoding="utf-8"))
            db.execute("INSERT INTO migrations (name) VALUES (%s)", (path.name,))


if __name__ == "__main__":
    with connect() as db:
        migrate(db)
