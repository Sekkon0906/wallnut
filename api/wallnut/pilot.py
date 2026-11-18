"""Arranque y comprobaciones del entorno institucional de Wallnut."""

import argparse
import os
from pathlib import Path
from re import fullmatch
from urllib.parse import urlsplit

import psycopg
import uvicorn
from psycopg.conninfo import conninfo_to_dict

from .database import connect, connection_string, migrate, migration_files, pending_migrations


class PilotError(Exception):
    pass


def validate_settings():
    try:
        origin = urlsplit(os.environ.get("WALLNUT_PUBLIC_ORIGIN", ""))
        if (origin.scheme != "https" or not origin.hostname or origin.username is not None or origin.port == 0
                or any(character.isspace() for character in origin.hostname)
                or origin.path not in ("", "/") or origin.query or origin.fragment):
            raise ValueError
    except ValueError as error:
        raise PilotError("WALLNUT_PUBLIC_ORIGIN debe contener el origen HTTPS del piloto.") from error

    ids = [item.strip() for item in os.environ.get("GOOGLE_CLIENT_IDS", "").split(",") if item.strip()]
    oauth_pending = os.environ.get("WALLNUT_ALLOW_UNCONFIGURED_OAUTH") == "true"
    if (not ids and not oauth_pending) or any(
        not fullmatch(r"[a-zA-Z0-9_-]+\.apps\.googleusercontent\.com", item) for item in ids
    ):
        raise PilotError("Configura GOOGLE_CLIENT_IDS con los identificadores OAuth de Google.")

    try:
        database = conninfo_to_dict(connection_string()).get("dbname")
    except (KeyError, psycopg.Error) as error:
        raise PilotError("Configura la conexión a PostgreSQL para el piloto.") from error
    if not database or database.lower() == "wallnut_demo":
        raise PilotError("Usa una base de datos dedicada al piloto, distinta de wallnut_demo.")

    web_dist = os.environ.get("WEB_DIST_DIR")
    required = ("index.html", "manifest.webmanifest", "sw.js")
    if not web_dist or any(not (Path(web_dist) / name).is_file() for name in required):
        raise PilotError("WEB_DIST_DIR debe apuntar a la web compilada con su manifiesto y service worker.")
    if not migration_files():
        raise PilotError("Faltan las migraciones SQL de Wallnut.")


def main():
    parser = argparse.ArgumentParser(description="Comprobación y arranque del piloto de Wallnut.")
    parser.add_argument("--check", action="store_true", help="Comprueba el entorno sin modificar la base.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=os.environ.get("PORT", "8080"))
    args = parser.parse_args()

    try:
        validate_settings()
        with connect() as db:
            if args.check:
                pending = pending_migrations(db)
                if pending:
                    raise PilotError(f"Hay {len(pending)} migraciones pendientes. Inicia el servicio del piloto.")
            else:
                migrate(db)
    except PilotError as error:
        parser.exit(1, f"Piloto: {error}\n")
    except psycopg.Error:
        parser.exit(1, "Piloto: PostgreSQL no está disponible o no se pudo preparar el esquema.\n")

    if args.check:
        print("Piloto: configuración, archivos web y esquema PostgreSQL verificados.")
        return
    uvicorn.run("wallnut.main:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
