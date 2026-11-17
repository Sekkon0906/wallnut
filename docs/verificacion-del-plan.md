# Verificación del plan de Wallnut

**Corte · versión 0.12.0**

Wallnut usa el [plan de arquitectura](plan-de-desarrollo-y-arquitectura.md) como punto de partida. Esta revisión separa la evidencia de desarrollo de las validaciones necesarias en el entorno institucional.

## Estado por módulo

| Módulo | Disponible para probar | Pendiente del piloto |
|---|---|---|
| Identidad y roles | Sesiones y funciones por rol, con verificación de identidad simulada en las pruebas. | Probar OAuth con el dominio, el cliente autorizado y cuentas reales de los tres roles. |
| Comunidad y perfiles | Eventos, publicaciones con foto, perfiles voluntarios, reportes y moderación. Comunidad organiza el contenido por secciones. | Definir responsables y tiempos de moderación. Revisar si hace falta ordenar todas las fuentes en una sola lista. |
| Talleres y evidencias | Convocatoria, selección, agenda, inscripción, asistencia, entrega, revisión y recompensa. | Probar el QR y el código manual entre dos equipos. Revisar cancelación de talleres y seguimiento de inscritos. |
| Billetera y canje académico | Saldos y movimientos, transferencias internas, cupos docentes y canje con nota simulada. | Acordar con el tutor la elegibilidad y la procedencia de los Coins usados para canjear Points. |
| Ardy y ranking | Editor 2D, armario, tienda, nueces y ranking voluntario. | Prototipo 3D y prueba de rendimiento en teléfonos del piloto. |
| Eventos y torneos | Modalidad individual y por parejas, inscripciones, cuadro, pase directo, marcadores y campeón. | Validar un torneo real con organizador y estudiantes. Confirmar la disponibilidad del espacio por el canal institucional. |
| Ayuda de Ardi | Temas frecuentes y preguntas en español con accesos según el rol. | Revisar las preguntas sin respuesta durante el piloto y ajustar las guías. |
| Operación y evaluación | Pruebas de API, APK de demostración, arranque con Compose, verificación del esquema y restauración de prueba. | Habilitar el entorno HTTPS institucional, probar iPhone y Android físicos, configurar los respaldos del entorno y evaluar su uso. |

## Alcance de torneos por parejas

El aforo se expresa en cupos para estudiantes. Ambos integrantes se inscriben en el evento. Uno envía la invitación y el otro la acepta. Solo los inscritos ven a las personas elegibles y las invitaciones se limitan a sus destinatarios. Cuando el organizador publica el cuadro se cierra el registro. Las parejas confirmadas quedan en la lista de participantes del cuadro, que avanza a ambos integrantes con cada victoria.

Antes de publicar, el organizador puede ver cuántos inscritos siguen sin pareja. Si publica con al menos dos parejas completas, los inscritos que siguen solos quedan fuera del cuadro. Si alguien libera su cupo antes del cierre, se retiran su pareja y las invitaciones vinculadas a esa inscripción.

## Validación institucional

La [guía de despliegue](despliegue-del-piloto.md) reúne la configuración, el arranque y el ensayo de recuperación de la base.

Una ronda de aceptación requiere un entorno HTTPS, una cuenta de cada rol y al menos un iPhone y un Android físicos. Se propone registrar el dispositivo, la versión, el resultado esperado y el resultado observado para cada recorrido.

1. **Acceso**. Entrar con cuentas institucionales de estudiante, docente y administración. Confirmar que la sesión se recupera al recargar y que cada rol accede a sus funciones.
2. **Instalación**. Instalar la web desde Safari y abrir Android con el entorno HTTPS. Cerrar la app, volver a abrir y revisar que se recupera la sesión.
3. **Taller**. Publicar, seleccionar tallerista, inscribir, registrar una asistencia por QR entre dos dispositivos y otra por código manual. Subir evidencia y acreditar una sola recompensa.
4. **Economía**. Pagar Coins por QR y repetir la misma solicitud. Solicitar un canje con nota simulada. Comprobar saldos, reserva, aprobación o devolución con motivo.
5. **Comunidad**. Reportar y moderar una foto. Inscribir y confirmar dos parejas. Publicar el cuadro, cerrar inscripciones y registrar el resultado.

Para el informe de grado, conservar evidencia de estos recorridos con cuentas de prueba y resultados agregados. Antes de usar datos institucionales, acordar el responsable operativo y la retención de evidencias.
