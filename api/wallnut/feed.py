from base64 import b64decode, urlsafe_b64encode
from binascii import Error as Base64Error
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import AwareDatetime, BaseModel, ValidationError

from .community import CALLS
from .database import Database
from .events import EVENTS
from .identity import CurrentAccount
from .social import POST_FIELDS, POSTS

router = APIRouter(tags=["Feed de Comunidad"])
Kind = Literal["post", "event", "call"]


class FeedCursor(BaseModel):
    published_at: AwareDatetime
    id: UUID
    kind: Kind


class FeedEntry(FeedCursor):
    institutional: bool
    content: dict[str, Any]


class FeedPage(BaseModel):
    items: list[FeedEntry]
    next_cursor: str | None


def encode_cursor(row):
    data = FeedCursor.model_validate(row).model_dump_json().encode()
    return urlsafe_b64encode(data).decode().rstrip("=")


def decode_cursor(value):
    try:
        data = b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        return FeedCursor.model_validate_json(data)
    except (Base64Error, ValidationError, ValueError) as error:
        raise HTTPException(422, "La página del feed no es válida. Actualiza Comunidad.") from error


@router.get("/community-feed", response_model=FeedPage)
def read_feed(
    account: CurrentAccount, db: Database, response: Response,
    limit: Annotated[int, Query(ge=1, le=30)] = 15,
    kind: Literal["all", "post", "event", "call"] = "all",
    origin: Literal["all", "university", "students"] = "all",
    cursor: Annotated[str | None, Query(max_length=400)] = None,
):
    after = decode_cursor(cursor) if cursor else None
    parameters = {
        "viewer": account.id, "student": account.id, "faculty": account.role == "faculty",
        "kind": kind, "origin": origin, "limit": limit + 1,
        "after_date": after.published_at if after else None,
        "after_id": after.id if after else None, "after_kind": after.kind if after else None,
    }
    candidates = db.execute(
        """
        SELECT * FROM (
            SELECT s.id, s.created_at AS published_at, 'post' AS kind,
                   a.role <> 'student' AS institutional
            FROM social_posts s JOIN accounts a ON a.id = s.author_id
            WHERE s.deleted_at IS NULL AND (s.hidden_at IS NULL OR s.author_id = %(viewer)s)
              AND %(kind)s IN ('all', 'post')
            UNION ALL
            SELECT e.id, e.created_at, 'event', e.institutional
            FROM campus_events e WHERE %(kind)s IN ('all', 'event')
            UNION ALL
            SELECT c.id, c.created_at, 'call', true
            FROM workshop_calls c WHERE %(kind)s IN ('all', 'call')
        ) entries
        WHERE (%(origin)s = 'all' OR institutional = (%(origin)s = 'university'))
          AND (%(after_date)s::timestamptz IS NULL
               OR (published_at, id, kind) < (%(after_date)s, %(after_id)s::uuid, %(after_kind)s::text))
        ORDER BY published_at DESC, id DESC, kind DESC LIMIT %(limit)s
        """, parameters,
    ).fetchall()

    page = candidates[:limit]
    content = {}
    queries = {
        "post": "SELECT " + POST_FIELDS + POSTS + """
            WHERE s.id = ANY(%(ids)s::uuid[]) AND s.deleted_at IS NULL
              AND (s.hidden_at IS NULL OR s.author_id = %(viewer)s)
        """,
        "event": EVENTS + " WHERE e.id = ANY(%(ids)s::uuid[])",
        "call": CALLS + " WHERE c.id = ANY(%(ids)s::uuid[])",
    }
    for entry_kind, query in queries.items():
        ids = [row["id"] for row in page if row["kind"] == entry_kind]
        if ids:
            rows = db.execute(query, {**parameters, "ids": ids}).fetchall()
            content.update({(entry_kind, row["id"]): row for row in rows})

    response.headers["Cache-Control"] = "private, no-store"
    return {
        "items": [{**row, "content": content[(row["kind"], row["id"])]}
                  for row in page if (row["kind"], row["id"]) in content],
        "next_cursor": encode_cursor(page[-1]) if len(candidates) > limit else None,
    }
