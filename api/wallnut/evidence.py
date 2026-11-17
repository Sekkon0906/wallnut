from io import BytesIO
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import AwareDatetime, BaseModel, StringConstraints

from .database import Database
from .economy import credit_approved_evidence
from .identity import CurrentAccount
from .workshops import is_assigned_faculty, is_facilitator, require_active_workshop

router = APIRouter(prefix="/workshops/{workshop_id}/evidence", tags=["Evidencias"])

MAX_PHOTO_BYTES = 8 * 1024 * 1024
MAX_PHOTO_PIXELS = 24_000_000
MAX_PHOTO_SIZE = (1600, 1600)
PHOTO_FORMATS = ("JPEG", "PNG", "WEBP")
PHOTO_TYPE = "image/jpeg"
PRIVATE_CACHE = {"Cache-Control": "private, no-store"}

EvidenceStatus = Literal["submitted", "returned", "approved"]
Reflection = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Comment = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]

SUMMARY_SQL = """
    SELECT e.id, e.student_id, a.display_name, e.reflection, e.status,
           e.comment, e.submitted_at, e.photo_content_type,
           coalesce(reward.points, 0) AS points_awarded,
           coalesce(CASE WHEN e.student_id = w.facilitator_id
                         THEN policy.facilitator_points ELSE policy.attendee_points END, 0)
               AS reward_points,
           goal.id IS NOT NULL AS goal_verified
    FROM workshop_evidence e JOIN accounts a ON a.id = e.student_id
    JOIN workshops w ON w.id = e.workshop_id
    LEFT JOIN workshop_economies policy ON policy.workshop_id = w.id
    LEFT JOIN wallet_movements reward ON reward.evidence_id = e.id AND reward.kind = 'evidence_reward'
    LEFT JOIN wallet_movements goal ON goal.evidence_id = e.id AND goal.kind = 'goal_coins'
"""


class EvidenceRecord(BaseModel):
    id: UUID
    student_id: UUID
    display_name: str
    reflection: str
    status: EvidenceStatus
    comment: str | None
    submitted_at: AwareDatetime
    photo_content_type: Literal["image/jpeg"]
    points_awarded: int
    reward_points: int
    goal_verified: bool


class EvidenceReview(BaseModel):
    decision: Literal["approved", "returned"]
    comment: Comment | None = None
    submitted_at: AwareDatetime | None = None


def get_workshop(db, workshop_id):
    workshop = db.execute(
        """
        SELECT w.id, w.facilitator_id, w.starts_at <= now() AS started, w.cancelled_at, c.faculty_id
        FROM workshops w JOIN workshop_calls p ON p.id = w.call_id
        JOIN course_sections c ON c.id = p.course_id
        WHERE w.id = %s
        """,
        (workshop_id,),
    ).fetchone()
    if not workshop:
        raise HTTPException(404, "No encontramos el taller.")
    return workshop


def require_reviewer(workshop, account):
    if not is_assigned_faculty(workshop, account):
        raise HTTPException(403, "Solo el docente asignado puede revisar las evidencias.")


def require_submitter(db, workshop_id, workshop, account):
    if account.role != "student":
        raise HTTPException(403, "Las evidencias se entregan desde una cuenta de estudiante.")
    require_active_workshop(workshop)
    if is_facilitator(workshop, account):
        if not workshop["started"]:
            raise HTTPException(409, "Podrás entregar la evidencia cuando comience el taller.")
        return
    attended = db.execute(
        "SELECT 1 FROM workshop_attendance WHERE workshop_id = %s AND student_id = %s",
        (workshop_id, account.id),
    ).fetchone()
    if not attended:
        raise HTTPException(409, "Registra tu asistencia antes de entregar la evidencia.")


def sanitize_photo(photo):
    if photo.size is not None and photo.size > MAX_PHOTO_BYTES:
        raise HTTPException(413, "La foto debe pesar 8 MiB o menos.")
    data = photo.file.read(MAX_PHOTO_BYTES + 1)
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(413, "La foto debe pesar 8 MiB o menos.")
    try:
        with Image.open(BytesIO(data), formats=PHOTO_FORMATS) as image:
            if image.width * image.height > MAX_PHOTO_PIXELS:
                raise HTTPException(413, "La foto debe tener 24 megapíxeles o menos.")
            if getattr(image, "is_animated", False):
                raise HTTPException(415, "Selecciona una foto estática en JPG, PNG o WebP.")
            image.thumbnail(MAX_PHOTO_SIZE)
            oriented = ImageOps.exif_transpose(image).convert("RGBA")
            # A new image retains the pixels and drops the uploaded metadata.
            normalized = Image.new("RGB", oriented.size, "white")
            normalized.paste(oriented, mask=oriented.getchannel("A"))
            result = BytesIO()
            normalized.save(result, format="JPEG", quality=85, optimize=True)
            return result.getvalue()
    except Image.DecompressionBombError as exc:
        raise HTTPException(413, "La foto debe tener 24 megapíxeles o menos.") from exc
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise HTTPException(415, "Selecciona una foto válida en JPG, PNG o WebP.") from exc


def get_evidence(db, evidence_id):
    return db.execute(SUMMARY_SQL + " WHERE e.id = %s", (evidence_id,)).fetchone()


@router.get("", response_model=list[EvidenceRecord])
def list_evidence(workshop_id: UUID, account: CurrentAccount, db: Database, response: Response):
    workshop = get_workshop(db, workshop_id)
    where = "WHERE e.workshop_id = %s"
    params = [workshop_id]
    if account.role == "student":
        where += " AND e.student_id = %s"
        params.append(account.id)
    else:
        require_reviewer(workshop, account)
    response.headers.update(PRIVATE_CACHE)
    return db.execute(SUMMARY_SQL + where + " ORDER BY e.submitted_at DESC, e.id", params).fetchall()


@router.post("", response_model=EvidenceRecord, status_code=201)
def submit_evidence(workshop_id: UUID, account: CurrentAccount, db: Database, response: Response,
                    photo: Annotated[UploadFile, File()], reflection: Annotated[Reflection, Form()]):
    workshop = get_workshop(db, workshop_id)
    require_submitter(db, workshop_id, workshop, account)
    normalized_photo = sanitize_photo(photo)
    with db.transaction():
        submitted = db.execute(
            """
            INSERT INTO workshop_evidence
                (workshop_id, student_id, reflection, photo, photo_content_type)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (workshop_id, student_id) DO UPDATE SET
                reflection = EXCLUDED.reflection,
                photo = EXCLUDED.photo,
                photo_content_type = EXCLUDED.photo_content_type,
                status = 'submitted',
                comment = NULL,
                submitted_at = clock_timestamp(),
                reviewed_by = NULL,
                reviewed_at = NULL
            WHERE workshop_evidence.status = 'returned'
            RETURNING id
            """,
            (workshop_id, account.id, reflection, normalized_photo, PHOTO_TYPE),
        ).fetchone()
        if not submitted:
            raise HTTPException(409, "Tu evidencia ya está en revisión o aprobada.")
        result = get_evidence(db, submitted["id"])
    response.headers.update(PRIVATE_CACHE)
    return result


@router.get("/{evidence_id}/photo", response_class=Response)
def download_photo(workshop_id: UUID, evidence_id: UUID, account: CurrentAccount, db: Database):
    workshop = get_workshop(db, workshop_id)
    where = "WHERE workshop_id = %s AND id = %s"
    params = [workshop_id, evidence_id]
    if account.role == "student":
        where += " AND student_id = %s"
        params.append(account.id)
    else:
        require_reviewer(workshop, account)
    evidence = db.execute(
        "SELECT photo, photo_content_type FROM workshop_evidence " + where, params,
    ).fetchone()
    if not evidence:
        raise HTTPException(404, "No encontramos la foto.")
    return Response(evidence["photo"], media_type=evidence["photo_content_type"], headers={
        **PRIVATE_CACHE,
        "Content-Disposition": 'inline; filename="evidencia.jpg"',
        "X-Content-Type-Options": "nosniff",
    })


@router.put("/{evidence_id}/review", response_model=EvidenceRecord)
def review_evidence(workshop_id: UUID, evidence_id: UUID, body: EvidenceReview,
                    account: CurrentAccount, db: Database, response: Response):
    workshop = get_workshop(db, workshop_id)
    require_reviewer(workshop, account)
    comment = body.comment or None
    if body.decision == "returned" and not comment:
        raise HTTPException(422, "Escribe un comentario para devolver la evidencia.")

    with db.transaction():
        evidence = db.execute(
            """
            SELECT id, student_id, status, comment, submitted_at FROM workshop_evidence
            WHERE workshop_id = %s AND id = %s FOR UPDATE
            """,
            (workshop_id, evidence_id),
        ).fetchone()
        if not evidence:
            raise HTTPException(404, "No encontramos la evidencia.")
        if body.submitted_at is not None and body.submitted_at != evidence["submitted_at"]:
            raise HTTPException(409, "La evidencia cambió. Abre la entrega actual antes de revisarla.")
        if evidence["status"] == "submitted":
            db.execute(
                """
                UPDATE workshop_evidence SET status = %s, comment = %s,
                    reviewed_by = %s, reviewed_at = clock_timestamp()
                WHERE id = %s
                """,
                (body.decision, comment, account.id, evidence_id),
            )
            if body.decision == "approved":
                db.execute("SELECT id FROM workshops WHERE id = %s FOR SHARE", (workshop_id,))
                credit_approved_evidence(db, workshop, evidence)
        elif (evidence["status"], evidence["comment"]) != (body.decision, comment):
            raise HTTPException(409, "Esta versión de la evidencia ya fue revisada.")
        result = get_evidence(db, evidence_id)
    response.headers.update(PRIVATE_CACHE)
    return result
