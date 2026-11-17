from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, StrictBool, StringConstraints

from .ardy import Avatar
from .database import Database
from .identity import CurrentAccount

router = APIRouter(tags=["Perfiles del campus"])


class ProfileSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bio: Annotated[str, StringConstraints(strip_whitespace=True, max_length=280)] = ""
    visible: StrictBool = False
    show_career: StrictBool = False


class CampusProfile(BaseModel):
    display_name: str
    bio: str
    career: str | None
    avatar: Avatar


def require_student(account):
    if account.role != "student":
        raise HTTPException(403, "El perfil del campus está disponible para estudiantes.")


@router.get("/my-campus-profile", response_model=ProfileSettings)
def read_settings(account: CurrentAccount, db: Database, response: Response):
    require_student(account)
    settings = db.execute(
        "SELECT bio, visible, show_career FROM campus_profiles WHERE student_id = %s",
        (account.id,),
    ).fetchone()
    response.headers["Cache-Control"] = "private, no-store"
    return settings or ProfileSettings()


@router.put("/my-campus-profile", response_model=ProfileSettings)
def save_settings(body: ProfileSettings, account: CurrentAccount, db: Database, response: Response):
    require_student(account)
    db.execute(
        """
        INSERT INTO campus_profiles (student_id, bio, visible, show_career)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (student_id) DO UPDATE SET
            bio = EXCLUDED.bio, visible = EXCLUDED.visible,
            show_career = EXCLUDED.show_career, updated_at = clock_timestamp()
        """,
        (account.id, body.bio, body.visible, body.show_career),
    )
    response.headers["Cache-Control"] = "private, no-store"
    return body


@router.get("/campus-profiles/{student_id}", response_model=CampusProfile)
def read_campus_profile(student_id: UUID, account: CurrentAccount, db: Database, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    profile = db.execute(
        """
        SELECT a.display_name, p.bio, ardy.avatar,
               CASE WHEN p.show_career THEN ardy.career END AS career
        FROM campus_profiles p
        JOIN accounts a ON a.id = p.student_id
        LEFT JOIN ardy_profiles ardy ON ardy.student_id = p.student_id
        WHERE p.student_id = %s AND p.visible AND a.role = 'student'
        """,
        (student_id,),
    ).fetchone()
    if not profile:
        raise HTTPException(404, "Este perfil del campus no está disponible.",
                            headers={"Cache-Control": "private, no-store"})
    return {**profile, "avatar": profile["avatar"] or Avatar()}
