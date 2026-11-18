import re
import unicodedata
from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, StringConstraints

from .activities import list_activities
from .auth import Database, Member

router = APIRouter(prefix="/ardi", tags=["Ardi"])


class ChatMessage(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


@router.post("/messages")
def reply(body: ChatMessage, member: Member, db: Database):
    normalized = unicodedata.normalize("NFKD", body.message).encode("ascii", "ignore").decode()
    words = set(re.findall(r"[a-z]+", normalized.lower()))

    if words & {"ranking", "posicion", "clasificacion"}:
        answer = "El ranking suma los puntos que ganas al asistir. Puedes transferirlos sin perder tu posición por ese envío."
    elif words & {"enviar", "transfiero", "transferir", "transferencia", "envio"}:
        answer = "Abre Billetera y selecciona Enviar. Escribe el @usuario del estudiante y la cantidad de puntos."
    elif words & {"asistencia", "qr", "ganar", "reclamar", "escanear"}:
        answer = "Abre la actividad en Campus y escanea el QR del organizador mientras esté vigente. Cada actividad te premia una vez."
    elif words & {"actividades", "eventos", "actividad", "evento", "agenda"}:
        activities = list_activities(member, db)[:3]
        if not activities:
            answer = "Por ahora no hay actividades disponibles."
        else:
            lines = [f"• {activity['title']} · {activity['location']}" for activity in activities]
            answer = "Estas son las primeras actividades del catálogo. Consulta el horario en Campus.\n\n" + "\n".join(lines)
    elif words & {"puntos", "token", "precio", "valor", "ardis"}:
        answer = "Los puntos se ganan con la participación y circulan dentro de Wallnut. Su uso depende de los intercambios de la comunidad."
    else:
        answer = "Puedo orientarte sobre actividades, asistencia, transferencias y ranking. ¿Sobre cuál quieres preguntar?"

    return {"answer": answer}

