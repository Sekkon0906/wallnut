import os
from dataclasses import dataclass
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth import exceptions, jwt
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.id_token import verify_oauth2_token
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, Field, SecretStr

from .database import Database

router = APIRouter(prefix="/session", tags=["Sesión"])
STUDENT_DOMAIN = "estudiantesunibague.edu.co"
STAFF_DOMAIN = "unibague.edu.co"
ALLOWED_DOMAINS = {STUDENT_DOMAIN, STAFF_DOMAIN}
bearer = HTTPBearer(auto_error=False)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


class GoogleSignIn(BaseModel):
    credential: Annotated[SecretStr, Field(min_length=1, max_length=8192)]


@dataclass(frozen=True)
class InstitutionalIdentity:
    subject: str
    email: str
    name: str
    default_role: str


class Account(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str


class SessionResponse(BaseModel):
    token: str
    account: Account


class GoogleVerifier:
    def __init__(self, client_ids):
        self.client_ids = set(client_ids)

    def __call__(self, credential):
        if not self.client_ids:
            raise HTTPException(503, "El acceso institucional aún no está configurado.")
        try:
            # Se usa la audiencia sin verificar solo para elegir un cliente permitido.
            audience = jwt.decode(credential, verify=False).get("aud")
            if not isinstance(audience, str) or audience not in self.client_ids:
                raise ValueError("Unexpected audience")
            return verify_oauth2_token(credential, GoogleRequest(), audience)
        except exceptions.TransportError as error:
            raise HTTPException(503, "No fue posible consultar el acceso institucional.") from error
        except (ValueError, TypeError, exceptions.GoogleAuthError) as error:
            raise HTTPException(401, "No se pudo verificar la cuenta de Google.") from error


def configured_verifier():
    return GoogleVerifier(
        client_id.strip()
        for client_id in os.environ.get("GOOGLE_CLIENT_IDS", "").split(",")
        if client_id.strip()
    )


def institutional_identity(claims):
    email = claims.get("email")
    subject = claims.get("sub")
    if (
        not isinstance(email, str)
        or not isinstance(subject, str)
        or not subject
        or claims.get("email_verified") is not True
    ):
        raise HTTPException(403, "Usa una cuenta institucional verificada.")

    email = email.strip().lower()
    local_part, _, domain = email.rpartition("@")
    hosted_domain = claims.get("hd")
    if (
        not local_part or "@" in local_part or domain not in ALLOWED_DOMAINS
        or not isinstance(hosted_domain, str) or hosted_domain not in ALLOWED_DOMAINS
    ):
        raise HTTPException(403, "Usa una cuenta institucional de Unibagué.")
    full_name = claims.get("name")
    display_name = full_name.strip()[:100] if isinstance(full_name, str) else ""
    return InstitutionalIdentity(
        subject=subject,
        email=email,
        name=display_name or email.split("@", 1)[0],
        default_role="student" if domain == STUDENT_DOMAIN else "staff",
    )


def token_hash(token):
    return sha256(token.encode("utf-8")).digest()


def session_key(credentials: Credentials):
    if not credentials:
        raise HTTPException(401, "Inicia sesión para continuar.")
    return token_hash(credentials.credentials)


SessionKey = Annotated[bytes, Depends(session_key)]


def signed_in_account(key: SessionKey, db: Database):
    account = db.execute(
        """
        SELECT a.id, a.email, a.display_name, a.role
        FROM sessions s JOIN accounts a ON a.id = s.account_id
        WHERE s.token_hash = %s AND s.expires_at > now()
        """,
        (key,),
    ).fetchone()
    if not account:
        raise HTTPException(401, "Vuelve a iniciar sesión.")
    return Account.model_validate(account)


CurrentAccount = Annotated[Account, Depends(signed_in_account)]


@router.post("", response_model=SessionResponse)
def exchange_google_credential(body: GoogleSignIn, request: Request, response: Response,
                               db: Database):
    claims = request.app.state.verify_identity(body.credential.get_secret_value())
    identity = institutional_identity(claims)
    token = token_urlsafe(32)
    try:
        with db.transaction():
            account = db.execute(
                """
                INSERT INTO accounts (google_subject, email, display_name, role)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (google_subject) DO UPDATE
                    SET email = EXCLUDED.email, display_name = EXCLUDED.display_name
                    WHERE (accounts.role = 'student') = (EXCLUDED.role = 'student')
                RETURNING id, email, display_name, role
                """,
                (identity.subject, identity.email, identity.name, identity.default_role),
            ).fetchone()
            if not account:
                raise HTTPException(409, "Administración debe revisar el cambio de dominio de esta cuenta.")
            db.execute(
                """
                INSERT INTO sessions (token_hash, account_id, expires_at)
                VALUES (%s, %s, now() + interval '8 hours')
                """,
                (token_hash(token), account["id"]),
            )
    except UniqueViolation as error:
        raise HTTPException(409, "Ese correo ya está vinculado a otra cuenta.") from error
    response.headers["Cache-Control"] = "no-store"
    return {"token": token, "account": account}


@router.get("", response_model=Account)
def session(account: CurrentAccount):
    return account


@router.delete("", status_code=204)
def logout(key: SessionKey, db: Database):
    db.execute("DELETE FROM sessions WHERE token_hash = %s", (key,))
    return Response(status_code=204)
