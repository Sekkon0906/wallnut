import argparse

from .database import connect


def main():
    parser = argparse.ArgumentParser(description="Habilita la primera cuenta administradora de Wallnut.")
    parser.add_argument("email", help="Cuenta de personal que ya ingresó con Google institucional.")
    args = parser.parse_args()
    email = args.email.strip().lower()
    with connect() as db, db.transaction():
        db.execute("SELECT pg_advisory_xact_lock(614100)")
        current = db.execute("SELECT email FROM accounts WHERE role = 'admin' LIMIT 1").fetchone()
        if current:
            if current["email"] != email:
                parser.exit(1, "Ya existe una cuenta administradora.\n")
        else:
            updated = db.execute(
                """
                UPDATE accounts SET role = 'admin'
                WHERE email = %s AND role = 'staff' RETURNING id
                """,
                (email,),
            ).fetchone()
            if not updated:
                parser.exit(1, "La cuenta de personal debe iniciar sesión primero.\n")
    print("Cuenta administradora habilitada.")


if __name__ == "__main__":
    main()
