# Verificación del plan de Wallnut

**Corte · versión 0.16.0 y despliegue de Railway del 18 de noviembre de 2026**

Los recorridos de esta nota sirven para comprobar los criterios del [plan de arquitectura](plan-de-desarrollo-y-arquitectura.md). La [web de Railway](https://wallnut-production.up.railway.app) tiene el esquema listo y mantiene cerrado el acceso mientras se configura Google.

## Estado por módulo

| Módulo | Disponible para probar | Pendiente del piloto |
|---|---|---|
| Identidad y roles | Sesiones y funciones por rol con identidad simulada en las pruebas. Railway mantiene el acceso cerrado durante la preparación de Google. | Registrar el origen HTTPS en el cliente OAuth y probar cuentas institucionales de los tres roles. |
| Comunidad y perfiles | Eventos, publicaciones con foto, perfiles voluntarios, reportes y moderación. Comunidad organiza el contenido por secciones. | Unificar el feed cronológico con filtros. Definir responsables y tiempos de moderación. |
| Talleres y evidencias | Convocatoria, agenda, inscripción, asistencia, entrega, revisión y recompensa. Reprogramación y cancelación con historial. Lista de inscritos y control de asistencia para el docente asignado. | Probar el QR y el código manual entre dos equipos y verificar que los inscritos encuentran los avisos de agenda. |
| Billetera y canje académico | Saldos y movimientos, transferencias internas, cupos docentes y canje con nota simulada. | Acordar con el tutor la elegibilidad y la procedencia de los Coins usados para canjear Points. |
| Ardy y ranking | Editor con vistas 2D y 3D, armario, tienda, nueces y ranking voluntario. | Probar interacción y rendimiento en iPhone y Android físicos. |
| Eventos y torneos | Modalidad individual y por parejas, inscripciones, cuadro, pase directo, marcadores y campeón. | Validar un torneo real con organizador y estudiantes. Confirmar la disponibilidad del espacio por el canal institucional. |
| Ayuda de Ardi | Temas frecuentes y preguntas en español con accesos según el rol. | Revisar las preguntas sin respuesta durante el piloto y ajustar las guías. |
| Operación y evaluación | Web y API en HTTPS en Railway, PostgreSQL privado con volumen, arranque con Compose, restauración de prueba e informe semanal exportable. | Probar iPhone y Android físicos, configurar respaldos y acordar metas y muestra con el tutor. |

## Alcance de torneos por parejas

El aforo se expresa en cupos para estudiantes. Ambos integrantes se inscriben en el evento. Uno envía la invitación y el otro la acepta. Solo los inscritos ven a las personas elegibles y las invitaciones se limitan a sus destinatarios. Cuando el organizador publica el cuadro se cierra el registro. Las parejas confirmadas quedan en la lista de participantes del cuadro, que avanza a ambos integrantes con cada victoria.

Antes de publicar, el organizador puede ver cuántos inscritos siguen sin pareja. Si publica con al menos dos parejas completas, los inscritos que siguen solos quedan fuera del cuadro. Si alguien libera su cupo antes del cierre, se retiran su pareja y las invitaciones vinculadas a esa inscripción.

## Vista 3D de Ardy

El editor carga bajo demanda un modelo construido por piezas con Three.js. Usa los mismos datos del retrato 2D y del armario. La escena se vuelve a dibujar al editar, girar o cambiar el tamaño de la vista. Si el navegador carece de WebGL 2 o se pierde el contexto gráfico, el editor recupera el retrato 2D y conserva la edición en curso.

## Informe de evaluación

Administración puede consultar 4, 8 o 12 semanas y exportar el mismo informe en CSV. La semana empieza el lunes en hora de Colombia. Las cifras corresponden a inscripciones y operaciones, de modo que un estudiante puede contar en varios talleres. El CSV incluye la zona horaria, la fecha de corte y la hora de generación. Su contenido se limita a fechas y totales.

- **Talleres**. Se agrupan por fecha de inicio. Entran los talleres finalizados al corte y se excluyen los cancelados. Las asistencias, las evidencias entregadas y las aprobaciones corresponden a las mismas inscripciones. Se recoge el estado de las evidencias al generar el informe, incluidas las revisiones posteriores al corte. Las entregas del tallerista se evalúan por separado.
- **Eventos**. Se agrupan por inicio. Entran los eventos que ya iniciaron al corte, con sus inscripciones. Se excluyen los cancelados.
- **Billetera y armario**. Se cuentan premios, conversiones, pagos confirmados, canjes académicos aprobados y compras por fecha de la operación. Las nueces se agrupan por compra y el estado de apertura corresponde al momento de generar el informe.

## Lista de inscritos al taller

El docente asignado ve en Agenda el nombre de cada inscrito, su hora de asistencia en Colombia y el estado de su evidencia. Puede buscar por nombre, filtrar por asistencia y actualizar la lista durante el taller. El acceso se limita a ese docente y la consulta entrega solo los datos que necesita la lista. El historial conserva los inscritos si se cancela el taller.

## Validación institucional

La [guía de despliegue](despliegue-del-piloto.md) reúne la configuración, el arranque y el ensayo de recuperación de la base.

Una ronda de aceptación requiere un entorno HTTPS, una cuenta de cada rol y al menos un iPhone y un Android físicos. Se propone registrar el dispositivo, la versión, el resultado esperado y el resultado observado para cada recorrido.

1. **Acceso**. Entrar con cuentas institucionales de estudiante, docente y administración. Confirmar que la sesión se recupera al recargar y que cada rol accede a sus funciones.
2. **Instalación**. Instalar la web desde Safari y abrir Android con el entorno HTTPS. Cerrar la app, volver a abrir y revisar que se recupera la sesión.
3. **Taller**. Publicar, seleccionar tallerista, inscribir, registrar una asistencia por QR entre dos dispositivos y otra por código manual. Subir evidencia y acreditar una sola recompensa. Abrir «Ver inscritos» como docente y confirmar que la lista refleja la asistencia y la aprobación.
4. **Economía**. Pagar Coins por QR y repetir la misma solicitud. Solicitar un canje con nota simulada. Comprobar saldos, reserva, aprobación o devolución con motivo.
5. **Comunidad**. Reportar y moderar una foto. Inscribir y confirmar dos parejas. Publicar el cuadro, cerrar inscripciones y registrar el resultado.
6. **Ardy**. Cambiar de 2D a 3D, girar con un dedo y con los botones, probar una prenda del armario y guardar la apariencia. Volver a 2D y comprobar que conserva la apariencia guardada.
7. **Evaluación**. Comparar el recorrido de un taller de prueba con los totales para sus fechas. Exportar el CSV desde Administración y comprobar que las cuentas de estudiante y docente carecen de acceso al informe.

Para el informe de grado, conservar evidencia de estos recorridos con cuentas de prueba y resultados agregados. Antes de usar datos institucionales, acordar el responsable operativo y la retención de evidencias.
