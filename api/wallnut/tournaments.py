from random import SystemRandom
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Response
from pydantic import BaseModel, ConfigDict, StringConstraints

from .database import Database
from .identity import CurrentAccount

router = APIRouter(prefix="/campus-events/{event_id}/tournament", tags=["Torneos del campus"])


class MatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    winner_id: UUID
    score: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80, pattern=r"^[^\x00]*$")] | None = None


def tournament_event(db, event_id, *, lock=False):
    query = """
        SELECT id, title, starts_at, organizer_id, cancelled, category, tournament_format
        FROM campus_events
        WHERE id = %s
    """
    event = db.execute(query + (" FOR UPDATE" if lock else ""), (event_id,)).fetchone()
    if not event or event["category"] != "tournament":
        raise HTTPException(404, "No encontramos el torneo.")
    return event


def require_organizer(event, account):
    if event["organizer_id"] != account.id:
        raise HTTPException(403, "Solo quien organiza puede gestionar el cuadro.")
    if event["cancelled"]:
        raise HTTPException(409, "El torneo fue cancelado.")


def public_match(row):
    first = {"id": row["first_id"], "name": row["first_name"]} if row["first_id"] else None
    second = {"id": row["second_id"], "name": row["second_name"]} if row["second_id"] else None
    if row["winner_id"]:
        status = "completed" if second else "bye"
    else:
        status = "ready" if first and second else "waiting"
    return {"number": row["match_number"], "status": status, "first": first, "second": second,
            "winner_id": row["winner_id"], "score": row["score"]}


def tournament_view(db, event, account):
    matches = db.execute(
        """
        SELECT m.round_number, m.match_number, m.first_id, m.second_id, m.winner_id, m.score,
               concat_ws(' y ', a1.display_name, b1.display_name) AS first_name,
               concat_ws(' y ', a2.display_name, b2.display_name) AS second_name
        FROM tournament_matches m
        LEFT JOIN tournament_participants p1 ON p1.event_id = m.event_id AND p1.student_id = m.first_id
        LEFT JOIN tournament_participants p2 ON p2.event_id = m.event_id AND p2.student_id = m.second_id
        LEFT JOIN accounts a1 ON a1.id = m.first_id
        LEFT JOIN accounts a2 ON a2.id = m.second_id
        LEFT JOIN accounts b1 ON b1.id = p1.partner_id
        LEFT JOIN accounts b2 ON b2.id = p2.partner_id
        WHERE m.event_id = %s
        ORDER BY m.round_number, m.match_number
        """,
        (event["id"],),
    ).fetchall()
    participant_count = db.execute(
        "SELECT count(*) AS total FROM campus_event_enrollments WHERE event_id = %s",
        (event["id"],),
    ).fetchone()["total"]
    doubles = event["tournament_format"] == "doubles"
    entrant_count = participant_count
    if doubles:
        entrant_count = db.execute(
            "SELECT count(*) AS total FROM tournament_pairs WHERE event_id = %s AND accepted_at IS NOT NULL",
            (event["id"],),
        ).fetchone()["total"]
    rounds = {}
    for row in matches:
        rounds.setdefault(row["round_number"], []).append(public_match(row))

    champion = None
    if matches and matches[-1]["winner_id"]:
        final = rounds[matches[-1]["round_number"]][0]
        champion = final["first"] if final["first"]["id"] == final["winner_id"] else final["second"]

    if event["cancelled"]:
        state = "cancelled"
    elif champion:
        state = "completed"
    else:
        state = "in_progress" if matches else "registration"
    can_manage = account.id == event["organizer_id"] and not event["cancelled"]
    return {
        "event_id": event["id"],
        "title": event["title"],
        "starts_at": event["starts_at"],
        "state": state,
        "can_manage": can_manage,
        "can_generate": can_manage and not matches and entrant_count >= 2,
        "participant_count": participant_count,
        "entrant_count": entrant_count,
        "tournament_format": event["tournament_format"],
        "unpaired_count": participant_count - entrant_count * 2 if doubles else 0,
        "champion": champion,
        "rounds": [{"number": number, "matches": group} for number, group in rounds.items()],
    }


def seeded_matches(students):
    # La posición de cada cabeza de serie reparte los pases libres entre las mitades.
    size = 1 << (len(students) - 1).bit_length()
    seeds = [1, 2]
    for depth in range(2, size.bit_length()):
        seeds = [slot for seed in seeds for slot in (seed, (1 << depth) + 1 - seed)]

    rounds = [
        [[None, None, None] for _ in range(size >> depth)]
        for depth in range(1, size.bit_length())
    ]
    for index, match in enumerate(rounds[0]):
        first, second = seeds[index * 2:index * 2 + 2]
        match[0] = students[first - 1]
        if second <= len(students):
            match[1] = students[second - 1]
        elif len(rounds) > 1:
            match[2] = match[0]
            rounds[1][index // 2][index % 2] = match[0]
    return rounds


@router.get("")
def get_tournament(event_id: UUID, account: CurrentAccount, db: Database, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    with db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return tournament_view(db, tournament_event(db, event_id), account)


@router.post("/bracket")
def publish_bracket(event_id: UUID, account: CurrentAccount, db: Database, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    with db.transaction():
        event = tournament_event(db, event_id, lock=True)
        require_organizer(event, account)
        if db.execute("SELECT 1 FROM campus_tournaments WHERE event_id = %s", (event_id,)).fetchone():
            return tournament_view(db, event, account)

        doubles = event["tournament_format"] == "doubles"
        entry_query = (
            """
            SELECT inviter_id AS student_id, invitee_id AS partner_id
            FROM tournament_pairs WHERE event_id = %s AND accepted_at IS NOT NULL
            """
            if doubles else
            "SELECT student_id, NULL AS partner_id FROM campus_event_enrollments WHERE event_id = %s"
        )
        entries = db.execute(entry_query, (event_id,)).fetchall()
        if len(entries) < 2:
            who = "parejas confirmadas" if doubles else "estudiantes inscritos"
            raise HTTPException(409, f"Se necesitan al menos dos {who}.")
        SystemRandom().shuffle(entries)
        rounds = seeded_matches([entry["student_id"] for entry in entries])

        db.execute("INSERT INTO campus_tournaments (event_id) VALUES (%s)", (event_id,))
        with db.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO tournament_participants (event_id, student_id, partner_id)
                VALUES (%s, %s, %s)
                """,
                [(event_id, entry["student_id"], entry["partner_id"]) for entry in entries],
            )
            cursor.executemany(
                """
                INSERT INTO tournament_matches (event_id, round_number, match_number,
                                                first_id, second_id, winner_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [(event_id, number, position, *match)
                 for number, group in enumerate(rounds, 1)
                 for position, match in enumerate(group, 1)],
            )
        return tournament_view(db, event, account)


@router.put("/matches/{round_number}/{match_number}")
def record_result(event_id: UUID, round_number: Annotated[int, Path(ge=1, le=9)],
                  match_number: Annotated[int, Path(ge=1, le=256)], body: MatchResult,
                  account: CurrentAccount, db: Database, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    score = body.score or None
    with db.transaction():
        event = tournament_event(db, event_id, lock=True)
        require_organizer(event, account)
        match = db.execute(
            """
            SELECT first_id, second_id, winner_id, score
            FROM tournament_matches WHERE event_id = %s AND round_number = %s AND match_number = %s
            """,
            (event_id, round_number, match_number),
        ).fetchone()
        if not match:
            raise HTTPException(404, "No encontramos el partido.")
        if not match["first_id"] or not match["second_id"]:
            raise HTTPException(409, "Este partido no tiene dos participantes definidos.")
        if body.winner_id not in (match["first_id"], match["second_id"]):
            raise HTTPException(422, "El ganador debe ser un participante de este partido.")
        if match["winner_id"]:
            if (match["winner_id"], match["score"]) != (body.winner_id, score):
                raise HTTPException(409, "El resultado de este partido ya fue registrado.")
            return tournament_view(db, event, account)

        db.execute(
            """
            UPDATE tournament_matches SET winner_id = %s, score = %s
            WHERE event_id = %s AND round_number = %s AND match_number = %s
            """,
            (body.winner_id, score, event_id, round_number, match_number),
        )
        following_slot = "first_id" if match_number % 2 else "second_id"
        db.execute(
            f"""
            UPDATE tournament_matches SET {following_slot} = %s
            WHERE event_id = %s AND round_number = %s AND match_number = %s
            """,
            (body.winner_id, event_id, round_number + 1, (match_number + 1) // 2),
        )
        return tournament_view(db, event, account)
