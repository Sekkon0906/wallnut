from hashlib import sha256
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile
from pydantic import AwareDatetime, BaseModel, StrictBool, StringConstraints

from .campus import Admin
from .database import Database
from .evidence import PHOTO_TYPE, PRIVATE_CACHE, sanitize_photo
from .identity import CurrentAccount

router = APIRouter(tags=["Publicaciones del campus"])
PostBody = Annotated[str, Form(max_length=1200, pattern=r"^[^\x00]*$")]
PostPhoto = Annotated[UploadFile | None, File()]
Offset = Annotated[int, Query(ge=0)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500,
                                          pattern=r"^[^\x00]*$")]

POST_FIELDS = """
    s.id, s.author_id, a.display_name AS author,
    (a.role = 'student' AND coalesce(p.visible, false)) AS author_profile_visible,
    s.body, s.photo IS NOT NULL AS has_photo, s.author_id = %(viewer)s AS mine,
    s.created_at, s.updated_at, s.hidden_at IS NOT NULL AS hidden, s.moderation_reason,
    EXISTS (
        SELECT 1 FROM social_post_reports r
        WHERE r.post_id = s.id AND r.reporter_id = %(viewer)s AND r.revision = s.revision
    ) AS reported
"""
POSTS = """
    FROM social_posts s JOIN accounts a ON a.id = s.author_id
    LEFT JOIN campus_profiles p ON p.student_id = s.author_id
"""


class CampusPost(BaseModel):
    id: UUID
    author_id: UUID
    author: str
    author_profile_visible: bool
    body: str
    has_photo: bool
    mine: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime | None
    hidden: bool
    moderation_reason: str | None
    reported: bool


class ReportInput(BaseModel):
    reason: Reason


class ModerationInput(ReportInput):
    hidden: StrictBool


class PendingReport(BaseModel):
    post: CampusPost
    report_count: int
    latest_reason: str
    latest_at: AwareDatetime


def post_not_found():
    return HTTPException(404, "No encontramos esa publicación.", headers=PRIVATE_CACHE)


def summary(db, post_id, viewer):
    return db.execute(
        "SELECT " + POST_FIELDS + POSTS + " WHERE s.id = %(id)s",
        {"viewer": viewer, "id": post_id},
    ).fetchone()


def owner_post(db, post_id, owner, *, lock=False):
    row = db.execute(
        """
        SELECT author_id, body, photo IS NOT NULL AS has_photo, deleted_at, hidden_at
        FROM social_posts WHERE id = %s
        """ + (" FOR UPDATE" if lock else ""),
        (post_id,),
    ).fetchone()
    if row is None:
        raise post_not_found()
    if row["author_id"] != owner:
        if row["hidden_at"] or row["deleted_at"]:
            raise post_not_found()
        raise HTTPException(403, "Solo puedes cambiar tus propias publicaciones.")
    return row


def require_content(body, has_photo):
    if not body and not has_photo:
        raise HTTPException(422, "Escribe un texto o agrega una foto.")


@router.get("/posts", response_model=list[CampusPost])
def list_posts(account: CurrentAccount, db: Database, response: Response, offset: Offset = 0):
    response.headers.update(PRIVATE_CACHE)
    return db.execute(
        "SELECT " + POST_FIELDS + POSTS + """
        WHERE s.deleted_at IS NULL AND (s.hidden_at IS NULL OR s.author_id = %(viewer)s)
        ORDER BY s.created_at DESC, s.id DESC LIMIT 21 OFFSET %(offset)s
        """,
        {"viewer": account.id, "offset": offset},
    ).fetchall()


@router.get("/posts/{post_id}", response_model=CampusPost)
def read_post(post_id: UUID, account: CurrentAccount, db: Database, response: Response):
    response.headers.update(PRIVATE_CACHE)
    row = db.execute(
        "SELECT " + POST_FIELDS + POSTS + """
        WHERE s.id = %(id)s AND s.deleted_at IS NULL
          AND (s.hidden_at IS NULL OR s.author_id = %(viewer)s)
        """, {"id": post_id, "viewer": account.id},
    ).fetchone()
    if not row:
        raise post_not_found()
    return row


@router.post("/posts", response_model=CampusPost, status_code=201)
def create_post(account: CurrentAccount, db: Database, response: Response, id: Annotated[UUID, Form()],
                body: PostBody = "", photo: PostPhoto = None):
    if account.role not in {"student", "faculty", "admin"}:
        raise HTTPException(403, "Tu cuenta puede consultar y reportar publicaciones.")
    body = body.strip()
    require_content(body, photo is not None)
    image = sanitize_photo(photo) if photo is not None else None
    digest = sha256(sha256(body.encode("utf-8")).digest() + (image or b"")).digest()
    with db.transaction():
        db.execute(
            """
            INSERT INTO social_posts (id, author_id, body, photo, creation_digest)
            VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING
            """,
            (id, account.id, body, image, digest),
        )
        existing = db.execute(
            "SELECT author_id, creation_digest, deleted_at FROM social_posts WHERE id = %s FOR UPDATE", (id,)
        ).fetchone()
        if existing["author_id"] != account.id or existing["creation_digest"] != digest or existing["deleted_at"]:
            raise HTTPException(409, "Ese identificador ya está asociado a otra publicación.")
        result = summary(db, id, account.id)
    response.headers.update(PRIVATE_CACHE)
    return result


@router.put("/posts/{post_id}", response_model=CampusPost)
def edit_post(post_id: UUID, account: CurrentAccount, db: Database, response: Response,
              body: PostBody = "", photo: PostPhoto = None,
              remove_photo: Annotated[bool, Form()] = False):
    if photo is not None and remove_photo:
        raise HTTPException(422, "Elige si quieres reemplazar o retirar la foto.")
    if owner_post(db, post_id, account.id)["deleted_at"]:
        raise post_not_found()
    image = sanitize_photo(photo) if photo is not None else None
    with db.transaction():
        post = owner_post(db, post_id, account.id, lock=True)
        if post["deleted_at"]:
            raise post_not_found()
        content = body.strip()
        require_content(content, not remove_photo and (image is not None or post["has_photo"]))
        db.execute(
            """
            UPDATE social_posts SET body = %(body)s,
                photo = CASE WHEN %(remove)s THEN NULL ELSE coalesce(%(photo)s, photo) END,
                updated_at = clock_timestamp(), revision = revision + 1
            WHERE id = %(id)s AND (
                body <> %(body)s OR
                (%(remove)s AND photo IS NOT NULL) OR
                (%(photo)s::bytea IS NOT NULL AND photo IS DISTINCT FROM %(photo)s)
            )
            """,
            {"body": content, "remove": remove_photo, "photo": image, "id": post_id},
        )
        result = summary(db, post_id, account.id)
    response.headers.update(PRIVATE_CACHE)
    return result


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: UUID, account: CurrentAccount, db: Database):
    with db.transaction():
        post = owner_post(db, post_id, account.id, lock=True)
        if not post["deleted_at"]:
            db.execute(
                """
                UPDATE social_posts SET body = '', photo = NULL, deleted_at = clock_timestamp()
                WHERE id = %s
                """,
                (post_id,),
            )
    return Response(status_code=204, headers=PRIVATE_CACHE)


@router.get("/posts/{post_id}/photo", response_class=Response)
def read_photo(post_id: UUID, account: CurrentAccount, db: Database):
    photo = db.execute(
        """
        SELECT photo FROM social_posts
        WHERE id = %s AND deleted_at IS NULL AND photo IS NOT NULL
            AND (hidden_at IS NULL OR author_id = %s OR %s)
        """,
        (post_id, account.id, account.role == "admin"),
    ).fetchone()
    if photo is None:
        raise HTTPException(404, "No encontramos esa foto.", headers=PRIVATE_CACHE)
    return Response(photo["photo"], media_type=PHOTO_TYPE, headers={
        **PRIVATE_CACHE,
        "Content-Disposition": 'inline; filename="publicacion.jpg"',
        "X-Content-Type-Options": "nosniff",
    })


@router.post("/posts/{post_id}/report", status_code=204)
def report_post(post_id: UUID, body: ReportInput, account: CurrentAccount, db: Database):
    with db.transaction():
        row = db.execute(
            """
            SELECT author_id, revision FROM social_posts
            WHERE id = %s AND deleted_at IS NULL AND hidden_at IS NULL FOR UPDATE
            """,
            (post_id,),
        ).fetchone()
        if row is None:
            raise post_not_found()
        if row["author_id"] == account.id:
            raise HTTPException(403, "Puedes retirar tus publicaciones desde Comunidad.")
        db.execute(
            """
            INSERT INTO social_post_reports (post_id, reporter_id, revision, reason)
            VALUES (%s, %s, %s, %s) ON CONFLICT (post_id, reporter_id, revision) DO NOTHING
            """,
            (post_id, account.id, row["revision"], body.reason),
        )
    return Response(status_code=204, headers=PRIVATE_CACHE)


@router.get("/post-reports", response_model=list[PendingReport])
def list_reports(account: Admin, db: Database, response: Response, hidden: bool = False, offset: Offset = 0):
    response.headers.update(PRIVATE_CACHE)
    rows = db.execute(
        """
        WITH counts AS (
            SELECT post_id, count(*) AS report_count
            FROM social_post_reports WHERE %(hidden)s OR resolved_at IS NULL GROUP BY post_id
        )
        SELECT
        """ + POST_FIELDS + """,
        coalesce(c.report_count, 0) AS report_count,
        coalesce(latest.reason, s.moderation_reason) AS latest_reason,
        coalesce(latest.created_at, s.hidden_at) AS latest_at
        """ + POSTS + """
        LEFT JOIN counts c ON c.post_id = s.id
        LEFT JOIN LATERAL (
            SELECT reason, created_at FROM social_post_reports
            WHERE post_id = s.id AND (%(hidden)s OR resolved_at IS NULL)
            ORDER BY created_at DESC, reporter_id LIMIT 1
        ) latest ON true
        WHERE s.deleted_at IS NULL AND (s.hidden_at IS NOT NULL) = %(hidden)s
            AND (%(hidden)s OR c.report_count IS NOT NULL)
        ORDER BY latest_at DESC, s.id DESC LIMIT 21 OFFSET %(offset)s
        """,
        {"viewer": account.id, "hidden": hidden, "offset": offset},
    ).fetchall()
    return [{"post": row, "report_count": row["report_count"], "latest_reason": row["latest_reason"],
             "latest_at": row["latest_at"]} for row in rows]


@router.put("/posts/{post_id}/moderation", response_model=CampusPost)
def moderate_post(post_id: UUID, body: ModerationInput, account: Admin, db: Database, response: Response):
    with db.transaction():
        row = db.execute(
            """
            SELECT hidden_at, moderation_reason FROM social_posts
            WHERE id = %s AND deleted_at IS NULL FOR UPDATE
            """,
            (post_id,),
        ).fetchone()
        if row is None:
            raise post_not_found()
        resolved = db.execute(
            """
            UPDATE social_post_reports SET resolved_at = now()
            WHERE post_id = %s AND resolved_at IS NULL
            """,
            (post_id,),
        ).rowcount
        reason = body.reason if body.hidden else None
        changed = reason != row["moderation_reason"]
        if changed:
            db.execute(
                """
                UPDATE social_posts SET hidden_at = CASE WHEN %s THEN clock_timestamp() ELSE NULL END,
                    moderation_reason = %s
                WHERE id = %s
                """,
                (body.hidden, reason, post_id),
            )
        if changed or resolved:
            db.execute(
                """
                INSERT INTO social_post_moderation (post_id, admin_id, hidden, reason)
                VALUES (%s, %s, %s, %s)
                """,
                (post_id, account.id, body.hidden, body.reason),
            )
        result = summary(db, post_id, account.id)
    response.headers.update(PRIVATE_CACHE)
    return result
