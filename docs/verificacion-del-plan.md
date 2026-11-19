# Verificación del plan de Wallnut

**Corte · versión 0.20.0**

Los recorridos de esta nota sirven para comprobar los criterios del [plan de arquitectura](plan-de-desarrollo-y-arquitectura.md). La [web de Railway](https://wallnut-production.up.railway.app) tiene el esquema listo y mantiene cerrado el acceso mientras se configura Google.

## Estado por módulo

| Módulo | Disponible para probar | Pendiente del piloto |
|---|---|---|
| Identidad y roles | Sesiones y funciones por rol con identidad simulada en las pruebas. Railway mantiene el acceso cerrado durante la preparación de Google. | Registrar el origen HTTPS en el cliente OAuth y probar cuentas institucionales de los tres roles. |
| Comunidad y perfiles | Feed cronológico de publicaciones, eventos y convocatorias con filtro por procedencia, paginación y acceso a cada recurso. Fotos y perfiles conservan su visibilidad. | Definir responsables y tiempos de moderación. Probar el recorrido con cuentas institucionales. |
| Talleres y evidencias | Convocatoria, agenda, inscripción, asistencia, entrega, revisión y recompensa. Reprogramación y cancelación con historial. Lista de inscritos y control de asistencia para el docente asignado. | Probar el QR y el código manual entre dos equipos y verificar que los inscritos encuentran los avisos de agenda. |
| Billetera y canje académico | Historial completo con filtros de Points y Coins, reservas y comprobación de saldos. Pagos recuperables, historial de cupos docentes y canje con nota simulada. | Acordar con el tutor la elegibilidad y la procedencia de los Coins usados para canjear Points. |
| Ardy y ranking | Editor con vistas 2D y 3D, armario, tienda, nueces y ranking voluntario. | Probar interacción y rendimiento en iPhone y Android físicos. |
| Eventos y torneos | Modalidad individual y por parejas, inscripciones, cuadro, pase directo, marcadores y campeón. | Validar un torneo real con organizador y estudiantes. Confirmar la disponibilidad del espacio por el canal institucional. |
| Ayuda de Ardi | Temas frecuentes y preguntas en español con accesos según el rol. | Revisar las preguntas sin respuesta durante el piloto y ajustar las guías. |
| Operación y evaluación | Web y API en HTTPS en Railway, PostgreSQL privado, pruebas de API automáticas en cada cambio, restauración de prueba e informe semanal exportable. | Probar iPhone y Android físicos, configurar respaldos y acordar metas y muestra con el tutor. |

## Feed de Comunidad

La vista «Todo» mezcla publicaciones, eventos y convocatorias por fecha de publicación. El filtro de procedencia permite ver Universidad o estudiantes. Las pestañas por tipo conservan las acciones para crear y gestionar contenido. Cada tarjeta abre el recurso concreto para inscribirse, revisar el cuadro, postularse, editar o reportar según los permisos de la cuenta.

El feed carga una página cada vez. La posición de la última tarjeta identifica desde dónde continuar, de modo que las publicaciones nuevas aparecen al actualizar. Las ediciones conservan la fecha de publicación. Los eventos cancelados muestran su estado y las convocatorias reflejan si ya tienen tallerista.

La migración 016 agrega la fecha de creación de eventos. Los eventos anteriores reciben la fecha de aplicación de esa migración, dado que el esquema anterior guardaba únicamente su inicio programado. Las publicaciones ocultas se muestran solo a su autor, igual que en su sección, y las retiradas quedan fuera de la consulta.

## Recuperación de cobros y pagos

La tarjeta muestra hasta diez solicitudes recientes de la cuenta, con prioridad para los cobros pendientes. Al abrir una solicitud se consulta su estado actual. Un cobro pendiente reconstruye el QR con el mismo código y fecha de vencimiento. El comprobante de un pago incluye su fecha y distingue a la persona que pagó de quien recibió los Coins. El historial privado se consulta en el servidor y puede recuperarse al volver a entrar a la cuenta.

Si la confirmación se interrumpe, la tarjeta ofrece «Consultar resultado» antes de permitir otro intento. Esa consulta recupera el estado sin ejecutar un pago. Las solicitudes muestran su vencimiento al llegar la hora, y un intento con resultado incierto conserva la opción de consultar incluso después de esa hora. Los pagos completados se pueden volver a consultar y los reintentos tienen un único descuento.

La restauración de sesión conserva el intento de recuperación cuando falla la conexión. Las respuestas tardías de una sesión anterior se descartan al cambiar de cuenta. Si el navegador restringe el almacenamiento, la sesión funciona en memoria durante el uso de la página.

## Historial completo de la billetera

La billetera permite consultar todos los movimientos registrados con páginas de veinte, filtrar los que afectan a Points o Coins y abrir la referencia de cada operación. Los canjes de Coins a Points aparecen en ambos filtros porque afectan a ambas unidades. El resumen muestra los ingresos y gastos acumulados de la cuenta completa y separa los Points reservados para solicitudes académicas pendientes.

Al aprobar un canje académico, el gasto sustituye a la reserva. Al rechazarlo, la reserva se libera y la solicitud conserva su motivo en Canjes académicos. Un canje rechazado no se presenta como gasto. El resumen, los saldos y cada página comparten una consulta consistente. Una operación nueva aparece al actualizar. La comprobación compara los movimientos con el saldo calculado y las reservas, y mantiene intactos los registros.

El historial es privado y está disponible para la propia cuenta estudiantil. Las referencias permiten localizar una operación sin exponer fotografías, reflexiones, correos o notas. La migración 019 agrega índices de consulta para pagos completados, compras y canjes aprobados.

## Historial del cupo docente

Administración puede abrir los movimientos de cada docente habilitado. El docente consulta los de su propio cupo. El resumen muestra el total asignado, los Points acreditados por evidencias, los obtenidos mediante canjes de Coins y el saldo disponible. Cada movimiento conserva la fecha, su referencia y el origen de la asignación o el taller correspondiente. La consulta entrega esos datos operativos y mantiene las fotos, reflexiones y notas en sus secciones privadas.

El historial empieza por los movimientos más recientes y carga las páginas anteriores desde la última referencia consultada. Una asignación nueva aparece al actualizar. El resumen y cada página se consultan sobre la misma versión de los datos para evitar diferencias mientras se acredita una recompensa. Si el saldo guardado presenta una diferencia respecto a las asignaciones y acreditaciones, la pantalla muestra la cantidad por revisar. La consulta conserva los saldos y sus registros de origen.

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
4. **Economía**. Abrir «Ver movimientos» del cupo como Administración y como docente. Verificar una asignación, una recompensa y una conversión. Crear un cobro, recargar y recuperar su QR desde «Solicitudes recientes». Pagar Coins por QR o código, consultar el comprobante y repetir la solicitud para verificar un único descuento. En Billetera, probar los filtros y cargar movimientos anteriores. Solicitar un canje de nota simulada y comprobar saldo, reserva, aprobación o devolución con motivo.
5. **Comunidad**. Crear contenido de cada tipo, confirmar su orden en «Todo», filtrar por procedencia y abrir cada tarjeta. Cargar otra página después de una nueva publicación. Reportar y moderar una foto y verificar que se retira del feed de otro estudiante. Inscribir y confirmar dos parejas, publicar el cuadro y registrar el resultado.
6. **Ardy**. Cambiar de 2D a 3D, girar con un dedo y con los botones, probar una prenda del armario y guardar la apariencia. Volver a 2D y comprobar que conserva la apariencia guardada.
7. **Evaluación**. Comparar el recorrido de un taller de prueba con los totales para sus fechas. Exportar el CSV desde Administración y comprobar que las cuentas de estudiante y docente carecen de acceso al informe.

Para el informe de grado, conservar evidencia de estos recorridos con cuentas de prueba y resultados agregados. Antes de usar datos institucionales, acordar el responsable operativo y la retención de evidencias.
