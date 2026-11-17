from datetime import date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

from .campus import Admin
from .database import Database

router = APIRouter(tags=["Evaluación del piloto"])
CAMPUS_TIME = ZoneInfo("America/Bogota")


class PilotWeek(BaseModel):
    week: date
    workshops: int
    workshop_enrollments: int
    attendances: int
    evidence_delivered: int
    evidence_approved: int
    events: int
    event_enrollments: int
    points_awards: int
    coin_goal_awards: int
    coin_conversions: int
    coin_payments: int
    approved_redemptions: int
    item_purchases: int
    nuts_purchased: int
    nuts_opened: int


class PilotReport(BaseModel):
    generated_at: datetime
    through: date
    time_zone: str
    weeks: list[PilotWeek]


@router.get("/admin/pilot-metrics", response_model=PilotReport)
def pilot_metrics(
    admin: Admin, db: Database, response: Response,
    weeks: Annotated[int, Query(ge=1, le=12)] = 4,
    through: date | None = None,
):
    now = datetime.now(CAMPUS_TIME)
    end_day = through or now.date()
    if end_day > now.date() or end_day < date(2000, 1, 1):
        raise HTTPException(422, "Elige una fecha de corte válida hasta hoy.")
    last_monday = end_day - timedelta(days=end_day.weekday())
    start_day = last_monday - timedelta(weeks=weeks - 1)
    end = min(now, datetime.combine(end_day + timedelta(days=1), time.min, CAMPUS_TIME))

    # All comparisons use indexed timestamps so rows outside each week can be skipped.
    # Evidence status is a snapshot, grouped with the workshop it belongs to.
    data = db.execute(
        """
        WITH mondays AS (
            SELECT %(start)s::date + 7 * n AS week
            FROM generate_series(0, %(weeks)s - 1) AS n
        ), weeks AS (
            SELECT week, week::timestamp AT TIME ZONE %(zone)s AS starts_at,
                   LEAST((week + 7)::timestamp AT TIME ZONE %(zone)s, %(end)s) AS ends_at
            FROM mondays
        )
        SELECT week, workshops.*, events.*, wallet.*, payments.*, redemptions.*, items.*, nuts.*
        FROM weeks
        CROSS JOIN LATERAL (
            SELECT count(DISTINCT w.id) AS workshops,
                   count(e.student_id) AS workshop_enrollments,
                   count(a.student_id) AS attendances,
                   count(v.id) AS evidence_delivered,
                   count(v.id) FILTER (WHERE v.status = 'approved') AS evidence_approved
            FROM workshops w
            LEFT JOIN workshop_enrollments e ON e.workshop_id = w.id
            LEFT JOIN workshop_attendance a ON (a.workshop_id, a.student_id) = (e.workshop_id, e.student_id)
            LEFT JOIN workshop_evidence v ON (v.workshop_id, v.student_id) = (a.workshop_id, a.student_id)
            WHERE w.starts_at >= weeks.starts_at AND w.starts_at < weeks.ends_at
              AND w.ends_at <= %(end)s AND w.cancelled_at IS NULL
        ) workshops
        CROSS JOIN LATERAL (
            SELECT count(DISTINCT c.id) AS events, count(e.student_id) AS event_enrollments
            FROM campus_events c
            LEFT JOIN campus_event_enrollments e ON e.event_id = c.id
            WHERE c.starts_at >= weeks.starts_at AND c.starts_at < weeks.ends_at AND NOT c.cancelled
        ) events
        CROSS JOIN LATERAL (
            SELECT count(*) FILTER (WHERE kind = 'evidence_reward') AS points_awards,
                   count(*) FILTER (WHERE kind = 'goal_coins') AS coin_goal_awards,
                   count(*) FILTER (WHERE kind = 'coin_conversion') AS coin_conversions
            FROM wallet_movements
            WHERE created_at >= weeks.starts_at AND created_at < weeks.ends_at
        ) wallet
        CROSS JOIN LATERAL (
            SELECT count(*) AS coin_payments FROM coin_payment_requests
            WHERE paid_at >= weeks.starts_at AND paid_at < weeks.ends_at
        ) payments
        CROSS JOIN LATERAL (
            SELECT count(*) AS approved_redemptions FROM grade_redemptions
            WHERE reviewed_at >= weeks.starts_at AND reviewed_at < weeks.ends_at AND status = 'approved'
        ) redemptions
        CROSS JOIN LATERAL (
            SELECT count(*) AS item_purchases FROM ardy_item_purchases
            WHERE created_at >= weeks.starts_at AND created_at < weeks.ends_at
        ) items
        CROSS JOIN LATERAL (
            SELECT count(*) AS nuts_purchased, count(*) FILTER (WHERE taps = 3) AS nuts_opened
            FROM ardy_nuts
            WHERE created_at >= weeks.starts_at AND created_at < weeks.ends_at
        ) nuts
        ORDER BY week DESC
        """,
        {"start": start_day, "end": end, "weeks": weeks, "zone": CAMPUS_TIME.key},
    ).fetchall()
    response.headers["Cache-Control"] = "private, no-store"
    return {"generated_at": now, "through": end_day, "time_zone": CAMPUS_TIME.key, "weeks": data}
