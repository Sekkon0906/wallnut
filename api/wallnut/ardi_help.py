from dataclasses import dataclass
from re import findall
from typing import Annotated, Literal
from unicodedata import normalize

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, StringConstraints

from .identity import CurrentAccount

router = APIRouter(prefix="/ardi-help", tags=["Ayuda de Ardi"])
Destination = Literal["community", "events", "posts", "calls", "agenda", "groups", "wallet", "ardy", "ranking"]


@dataclass(frozen=True)
class Guide:
    answer: str
    action: Destination | None = None


@dataclass(frozen=True)
class Topic:
    id: str
    title: str
    keywords: tuple[str, ...]
    guides: dict[str, Guide]

    def for_role(self, role: str) -> Guide | None:
        return self.guides.get(role) or self.guides.get("all")


TOPICS = (
    Topic("workshops", "Talleres y convocatorias",
          ("taller", "talleres", "convocatoria", "convocatorias", "tallerista", "inscribo a un taller"),
          {
              "student": Guide(
                  "Abre Agenda y selecciona un taller con cupos para inscribirte. "
                  "Para dirigir un taller, abre Comunidad, entra en Convocatorias y elige Postularme.",
                  "agenda",
              ),
              "faculty": Guide(
                  "En Comunidad → Convocatorias publica una convocatoria para un grupo asignado. "
                  "Selecciona al tallerista y programa el taller con lugar, fecha y cupos.",
                  "calls",
              ),
              "all": Guide("En Agenda puedes consultar los talleres programados y su horario.", "agenda"),
          }),
    Topic("attendance", "Asistencia por QR",
          ("asistencia", "asistir", "registrar asistencia", "codigo de asistencia", "qr de asistencia",
           "escanear el qr del taller"),
          {
              "student": Guide(
                  "Si tienes un cupo, abre el taller en Agenda. Durante la actividad, escanea el QR "
                  "o ingresa el código manual que presenta quien dirige el taller. Si eres el tallerista "
                  "asignado, puedes generar el código desde el taller.",
                  "agenda",
              ),
              "faculty": Guide(
                  "Abre tu taller en Agenda durante la actividad y genera el QR de asistencia. "
                  "Comparte el código manual con quienes no puedan usar la cámara.",
                  "agenda",
              ),
              "all": Guide("La asistencia se registra en Agenda con el QR o el código de cada taller.", "agenda"),
          }),
    Topic("evidence", "Evidencias y metas",
          ("evidencia", "evidencias", "reflexion", "aprobar una evidencia", "meta verificada", "subir evidencia",
           "foto de evidencia"),
          {
              "student": Guide(
                  "Después de registrar asistencia, abre el taller en Agenda y envía una foto y una reflexión. "
                  "Si recibes una observación, corrige y reenvía. El docente verifica aparte la meta que puede otorgar Coins.",
                  "agenda",
              ),
              "faculty": Guide(
                  "Abre el taller en Agenda y revisa la entrega. Puedes aprobarla o devolverla con una observación. "
                  "Si se cumplió la meta configurada, elige Verificar meta y otorgar Coins.",
                  "agenda",
              ),
              "all": Guide("El docente asignado revisa las entregas y verifica las metas de su taller."),
          }),
    Topic("payments", "Pagos con Ardi Coins",
          ("coin", "coins", "monedas", "billetera", "wallet", "pagar", "pago", "cobrar", "transferir", "transferencia",
           "qr de pago", "codigo de pago", "recibir coins", "ardicoin", "ardicoins", "ardi coins"),
          {
              "student": Guide(
                  "En Billetera puedes consultar tu saldo y movimientos. Para cobrar, elige Recibir Coins. "
                  "Para pagar, abre Pagar con QR, escanea el código o pégalo, revisa a quién pagas y confirma. "
                  "Ganas Coins con metas verificadas por el docente. Los Coins son de uso interno y carecen de valor monetario.",
                  "wallet",
              ),
              "all": Guide("La Billetera estudiantil permite cobrar y pagar Ardi Coins de uso interno. "
                           "Una solicitud de pago vence en cinco minutos."),
          }),
    Topic("conversion", "Convertir Coins en Points",
          ("convertir coins", "coins en points", "coins por points", "coins a points", "convertir a points",
           "coins a ardi points", "coins por ardi points", "conversion"),
          {
              "student": Guide(
                  "En Billetera, mira Canjes por metas verificadas. Si tu docente verificó una meta y el taller "
                  "tiene un canje configurado, elige Canjear por Points. La pantalla indica el costo y los "
                  "Points que recibirías. El canje requiere Coins y cupo docente suficientes.",
                  "wallet",
              ),
              "faculty": Guide(
                  "En la configuración de recompensas de tu taller puedes definir el costo en Coins y los Points "
                  "del canje. Para que a un estudiante le aparezca esa opción, verifica su meta primero.",
                  "agenda",
              ),
          }),
    Topic("points", "Cómo ganar Ardi Points",
          ("point", "points", "puntos", "ardi points", "ardipoints", "ganar points", "puntos positivos"),
          {
              "student": Guide(
                  "Participa en un taller con recompensa y entrega la evidencia solicitada. Si el docente la aprueba, "
                  "los Points salen de su cupo y aparecen en Billetera con el taller y el grupo de origen. "
                  "Consulta los talleres en Agenda.",
                  "agenda",
              ),
              "all": Guide("Los Ardi Points se otorgan desde el cupo docente por actividades aprobadas. Cada movimiento "
                           "conserva el grupo de origen y las condiciones de canje."),
          }),
    Topic("grades", "Canje académico de Points",
          ("nota", "notas", "calificacion", "decima", "decimas", "subir la nota", "canje academico",
           "points por nota", "canjear points", "canjear mis points", "canjear puntos", "puntos para la nota"),
          {
              "student": Guide(
                  "En Mis grupos, abre el grupo y entra en Canje académico. Allí ves los Points que puedes usar, "
                  "la equivalencia y el tope. Al solicitar el ajuste, el saldo queda reservado hasta la decisión del "
                  "docente. El piloto usa notas simuladas.",
                  "groups",
              ),
              "faculty": Guide(
                  "En Mis grupos → Canje académico puedes configurar equivalencia, tope, mínimo y orígenes admitidos, "
                  "registrar la nota base simulada y revisar solicitudes.",
                  "groups",
              ),
          }),
    Topic("budgets", "Cupos docentes de Points",
          ("cupo docente", "cupos docentes", "asignar points", "asignar cupo", "presupuesto", "reponer points"),
          {
              "faculty": Guide(
                  "Consulta tu cupo de Points en Mis grupos. Define la recompensa de cada taller en Agenda. "
                  "Cuando falte saldo, solicita una asignación a Administración.",
                  "groups",
              ),
              "admin": Guide(
                  "En Administración → Cupos docentes, selecciona a la persona y la cantidad de Points. "
                  "La asignación queda registrada y se descuenta del saldo docente cuando se acredita una recompensa.",
                  "groups",
              ),
          }),
    Topic("events", "Eventos y torneos",
          ("evento", "eventos", "torneo", "torneos", "marcador", "eliminacion directa", "cuadro del torneo",
           "generar cuadro", "registrar resultado", "por parejas", "formar pareja", "enviar una invitacion"),
          {
              "student": Guide(
                  "En Comunidad → Eventos puedes inscribirte o crear un evento. Para un torneo por parejas, "
                  "ambos se inscriben y uno envía la invitación desde Ver cuadro → Mi pareja. "
                  "La otra persona debe aceptarla. En Ver cuadro también puedes seguir los partidos y resultados.",
                  "events",
              ),
              "all": Guide(
                  "En Comunidad → Eventos, usa Ver cuadro para consultar el torneo. Quien organiza "
                  "genera el cuadro con al menos dos participantes individuales o dos parejas confirmadas. "
                  "Al publicarlo cierra las inscripciones y puede registrar los ganadores y marcadores.",
                  "events",
              ),
          }),
    Topic("posts", "Publicaciones y reportes",
          ("publicacion", "publicaciones", "foto en el feed", "publicar una foto", "reportar", "reporte", "reportes",
           "moderar", "moderacion", "ocultar publicacion"),
          {
              "student": Guide(
                  "Ve a Comunidad → Publicaciones y elige Crear publicación para compartir texto o una foto. "
                  "Puedes editar lo tuyo o reportar una publicación de otra persona.",
                  "posts",
              ),
              "admin": Guide(
                  "Abre Comunidad → Publicaciones → Revisar reportes. Ahí puedes ocultar una publicación, "
                  "cerrar sus reportes o restaurarla desde Publicaciones ocultas.",
                  "posts",
              ),
              "all": Guide("En Comunidad → Publicaciones puedes consultar el contenido y reportarlo para revisión.",
                           "posts"),
          }),
    Topic("avatar", "Personalizar Ardy y mi perfil",
          ("ardy", "ardilla", "avatar", "carrera", "perfil", "personalizar", "mi ardy", "ocultar mi perfil"),
          {
              "student": Guide(
                  "Abre Mi Ardy para elegir una apariencia y guardar tu carrera. En Mi perfil del campus puedes "
                  "escribir tu presentación y decidir si muestras el perfil o la carrera.",
                  "ardy",
              ),
              "all": Guide("Los perfiles estudiantiles visibles se pueden abrir desde los eventos y las publicaciones "
                           "de su titular.", "community"),
          }),
    Topic("nuts", "Nueces y armario",
          ("nuez", "nueces", "armario", "rareza", "prenda", "ropa", "accesorio", "tienda", "abrir una nuez",
           "abro una nuez", "nuez con coins", "comprar una nuez"),
          {
              "student": Guide(
                  "En Mi Ardy → Tienda de Ardy puedes comprar una nuez con Coins y ver sus probabilidades. "
                  "Se abre en tres toques y la prenda pasa al armario. Si sales, usa Continuar apertura.",
                  "ardy",
              ),
          }),
    Topic("rank", "Ranking de participación",
          ("ranking", "clasificacion", "puesto", "posicion", "puntuacion", "tabla de participacion"),
          {
              "student": Guide(
                  "El Ranking suma los Points ganados con evidencias aprobadas. Para participar, abre Mi Ardy, "
                  "activa Mostrar mi nombre y mi Ardy en el ranking y guarda.",
                  "ranking",
              ),
              "all": Guide(
                  "El Ranking ordena a los estudiantes que eligieron aparecer por Points ganados con evidencias "
                  "aprobadas y, en caso de empate, por actividades verificadas.",
                  "ranking",
              ),
          }),
    Topic("access", "Acceso, roles y matrículas",
          ("acceso", "sesion", "login", "entrar", "correo institucional", "matricula", "matricular",
           "habilitar docente", "rol"),
          {
              "admin": Guide("En Administración puedes habilitar a un docente, asignarlo a un grupo "
                             "y confirmar matrículas con el correo institucional.", "groups"),
              "faculty": Guide("En Mis grupos puedes consultar tus grupos asignados y confirmar la matrícula de un "
                               "estudiante con su correo institucional.", "groups"),
              "staff": Guide("Entra con el correo institucional. Para gestionar grupos o publicar convocatorias, "
                             "solicita a Administración que habilite tu rol docente."),
              "student": Guide("Usa tu cuenta institucional de Google para entrar. Si falta una matrícula en Mis grupos, "
                               "pide al docente que la confirme con tu correo institucional.", "groups"),
          }),
)

FALLBACK = Guide("No encontré un tema que corresponda a esa pregunta. Prueba con el nombre de una sección "
                 "de Wallnut o elige uno de los temas frecuentes.")


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    topic: Annotated[str, StringConstraints(min_length=1, max_length=24, pattern=r"^[a-z-]+$")] | None = None


class TopicCard(BaseModel):
    id: str
    title: str


class TopicsResponse(BaseModel):
    topics: list[TopicCard]


class AnswerResponse(BaseModel):
    topic: str | None
    answer: str
    action: Destination | None


def find_topic(question: Question, available: list[Topic]) -> Topic | None:
    if question.topic:
        return next((topic for topic in available if topic.id == question.topic), None)

    words = " ".join(findall(r"[a-z0-9]+", normalize("NFKD", question.question.casefold())
                             .encode("ascii", "ignore").decode("ascii")))
    text = f" {words} "
    scores = {
        topic.id: sum((phrase.count(" ") + 1) ** 2 for phrase in topic.keywords if f" {phrase} " in text)
        for topic in available
    }
    best = max(scores.values(), default=0)
    if not best:
        return None
    matches = [topic for topic in available if scores[topic.id] == best]
    return matches[0] if len(matches) == 1 else None


@router.get("", response_model=TopicsResponse)
def list_topics(account: CurrentAccount, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return {"topics": [{"id": topic.id, "title": topic.title} for topic in TOPICS if topic.for_role(account.role)]}


@router.post("", response_model=AnswerResponse)
def answer_question(question: Question, account: CurrentAccount, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    available = [topic for topic in TOPICS if topic.for_role(account.role)]
    topic = find_topic(question, available)
    guide = topic.for_role(account.role) if topic else None
    answer = guide or FALLBACK
    return {"topic": topic.id if topic else None, "answer": answer.answer, "action": answer.action}
