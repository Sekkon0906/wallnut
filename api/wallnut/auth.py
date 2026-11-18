from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import Connection
from pwdlib import PasswordHash
from pydantic import BaseModel, Field, SecretStr, StringConstraints

from .db import database

router = APIRouter(prefix="/session", tags=["Sesión"])
password_hash = PasswordHash.recommended()
dummy_hash = password_hash.hash(token_urlsafe())
bearer = HTTPBearer(auto_error=False)
Database = Annotated[Connection, Depends(database)]
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


class Login(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=254)]
    password: Annotated[SecretStr, Field(min_length=1, max_length=128)]


def digest(value: str):
    return sha256(value.encode("utf-8")).hexdigest()


def require_session(credentials: Credentials):
    if not credentials:
        raise HTTPException(401, "Inicia sesión para continuar.")
    return digest(credentials.credentials)


Session = Annotated[str, Depends(require_session)]


def current_member(session: Session, db: Database):
    member = db.execute(
        """
        SELECT m.id, m.handle, m.display_name, m.role
        FROM sessions s JOIN members m ON m.id = s.member_id
        WHERE s.token_hash = %s AND s.expires_at > now()
        """,
        (session,),
    ).fetchone()
    if not member:
        raise HTTPException(401, "La sesión venció. Vuelve a iniciar sesión.")
    return member


Member = Annotated[dict, Depends(current_member)]


def require_organizer(member: Member):
    if member["role"] != "organizer":
        raise HTTPException(403, "Esta acción es para organizadores.")
    return member


Organizer = Annotated[dict, Depends(require_organizer)]


@router.post("")
def sign_in(body: Login, db: Database):
    member = db.execute(
        "SELECT id, handle, display_name, role, password_hash FROM members WHERE email = %s",
        (body.email.lower(),),
    ).fetchone()
    stored_hash = member.pop("password_hash") if member else dummy_hash
    if not password_hash.verify(body.password.get_secret_value(), stored_hash) or not member:
        raise HTTPException(401, "Correo o contraseña incorrectos.")

    token = token_urlsafe(32)
    db.execute(
        """
        INSERT INTO sessions (token_hash, member_id, expires_at)
        VALUES (%s, %s, now() + interval '12 hours')
        """,
        (digest(token), member["id"]),
    )
    return {"token": token, "member": member}


@router.delete("", status_code=204)
def sign_out(session: Session, db: Database):
    db.execute("DELETE FROM sessions WHERE token_hash = %s", (session,))

