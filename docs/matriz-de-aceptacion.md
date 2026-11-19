# Matriz de aceptación de Wallnut

**Base de aplicación 0.23.0 · 19 de noviembre de 2026**

La suite de esta entrega contiene 64 pruebas de API y 15 de sesión, transporte y conexión. El [historial de ejecuciones](https://github.com/Sekkon0906/wallnut/actions/workflows/pilot.yml) registra sus resultados, los tipos de la interfaz y el arranque y restauración del piloto. Esas pruebas usan cuentas y bases de prueba. Las filas siguientes identifican el caso que aporta evidencia para cada requisito.

El ensayo institucional continúa pendiente de Google OAuth y de dispositivos físicos. Un resultado automático demuestra el comportamiento cubierto por su prueba. El equipo registra aparte lo observado al ejecutar el recorrido con participantes, roles y equipos del piloto.

## Requisitos y evidencia automática

| ID | Requisito verificable | Evidencia de referencia |
| --- | --- | --- |
| W-ID-01 | Verificar correo institucional, rechazar identidades no admitidas y cerrar la sesión. | [test_verified_signup_and_logout](../api/tests/test_pilot.py) |
| W-ID-02 | Conservar la sesión solo cuando se elige, retirarla al cerrar y verificar su vigencia antes de recuperar datos privados. | [Almacenamiento de sesión](../web/tests/sessionStorage.test.mjs) y [test_expired_session_cannot_restore_private_account_data](../api/tests/test_pilot.py). |
| W-ROL-01 | Gestionar grupos y matrículas según el rol autorizado. | [test_campus_and_confirmed_student_enrollment](../api/tests/test_pilot.py) |
| W-TAL-01 | Publicar una convocatoria y seleccionar un único tallerista ante dos decisiones simultáneas. | [test_only_one_parallel_approval_succeeds](../api/tests/test_pilot.py) |
| W-AFO-01 | Conservar el aforo ante inscripciones simultáneas y permitir liberar un cupo. | [test_capacity_survives_concurrent_signups_and_cancellation](../api/tests/test_workshops.py) |
| W-ASI-01 | Vincular el código temporal al taller y a un estudiante inscrito. | [test_attendance_code_is_workshop_bound_and_requires_enrollment](../api/tests/test_workshops.py) |
| W-EVI-01 | Restringir el acceso a las fotos académicas y normalizar el archivo recibido. | [test_evidence_access_and_photo_sanitization](../api/tests/test_evidence.py) |
| W-EVI-02 | Devolver, corregir y aprobar la versión actual de una evidencia. | [test_evidence_return_resubmit_and_approval](../api/tests/test_evidence.py) |
| W-PNT-01 | Acreditar la evidencia una sola vez desde el cupo docente. | [test_approved_evidence_draws_from_the_faculty_budget_once](../api/tests/test_wallet.py) |
| W-MET-01 | Verificar una meta y convertir Coins a Points sin duplicar sus efectos. | [test_verified_goal_and_conversion_are_idempotent_under_a_retry](../api/tests/test_wallet.py) |
| W-CUP-01 | Consultar asignaciones, acreditaciones y saldo del cupo con permiso del docente o Administración. | [Historial del cupo docente](../api/tests/test_faculty_ledger.py) |
| W-WAL-01 | Consultar todas las fuentes de billetera y separar las reservas de los gastos. | [Historial de billetera](../api/tests/test_wallet_history.py) |
| W-PAG-01 | Recuperar solicitudes y comprobantes y consultar una confirmación interrumpida con un único descuento. | [Recuperación de pagos](../api/tests/test_payment_recovery.py) |
| W-NOT-01 | Aplicar procedencias, mínimo y topes del canje con nota simulada. | [test_origin_policy_and_simulated_grade_limits](../api/tests/test_grade_redemptions.py) |
| W-NOT-02 | Reservar Points, consumirlos al aprobar y liberarlos al rechazar. | [test_redemption_reserves_releases_and_records_points_once](../api/tests/test_grade_redemptions.py) |
| W-RAN-01 | Calcular participación verificada y respetar la elección de aparecer en el ranking. | [test_ranking_counts_only_participation_and_respects_visibility](../api/tests/test_ardy.py) |
| W-NUE-01 | Mantener una sola compra de nuez, retomar sus toques y acreditar una sola prenda. | [Nueces de Ardy](../api/tests/test_ardy_nuts.py) |
| W-PER-01 | Aplicar la visibilidad del perfil en la navegación y en su acceso directo. | [test_campus_profile_visibility_controls_both_events_and_direct_access](../api/tests/test_campus_profiles.py) |
| W-SOC-01 | Deduplicar reportes y retirar el acceso comunitario a una foto ocultada. | [test_review_queue_deduplicates_reports_and_guards_hidden_photo](../api/tests/test_social_posts.py) |
| W-FED-01 | Ordenar el feed y continuar páginas con fechas coincidentes y publicaciones nuevas. | [Feed de Comunidad](../api/tests/test_community_feed.py) |
| W-TOR-01 | Generar y completar el cuadro individual con los permisos del organizador. | [Torneos individuales](../api/tests/test_tournaments.py) |
| W-PAR-01 | Confirmar parejas y avanzar a ambos integrantes en el cuadro. | [Torneos por parejas](../api/tests/test_tournament_pairs.py) |
| W-AVI-01 | Notificar a los destinatarios actuales y conservar los avisos posteriores a una marca de lectura. | [Avisos del campus](../api/tests/test_notifications.py) |
| W-RED-01 | Mantener un único intento de envío y distinguir respuestas perdidas, vencidas o truncadas. | [Transporte web](../web/tests/transport.test.mjs) |
| W-RED-02 | Evitar que una respuesta anterior sustituya a una comprobación posterior de conexión. | [Estado de conexión](../web/tests/connectivity.test.mjs) |
| W-INF-01 | Restringir el informe a Administración y contar operaciones y etapas en hora de Colombia. | [Indicadores del piloto](../api/tests/test_pilot_metrics.py) |
| W-OPS-01 | Comprobar esquema y configuración y mantener cerrado el acceso cuando falta Google. | [Preparación del despliegue](../api/tests/test_pilot_deployment.py) y trabajo `pilot` de la ejecución de referencia. |

## Recorridos de aceptación institucional

Todas las filas de esta tabla parten en **Pendiente**. El responsable cambia el estado después de registrar el resultado observado y su evidencia en la ficha inferior. Los requisitos relacionados identifican las verificaciones automáticas que acompañan al recorrido.

| Caso | Roles y preparación | Recorrido y resultado esperado | Requisitos |
| --- | --- | --- | --- |
| A-01 · Acceso | Cuenta de estudiante, docente y Administración; cuenta externa de prueba. | Entrar, recargar, cerrar y probar acceso a una función de otro rol. La cuenta admitida recupera su vista y los accesos indebidos se rechazan. | W-ID-01, W-ROL-01 |
| A-02 · Instalación | iPhone y Android físicos con acceso HTTPS. Probar retención activada y desactivada. | Instalar la PWA desde Safari y abrir Android con su configuración institucional. Cerrar y abrir. Con retención elegida, recuperar la sesión vigente tras su verificación. Sin retención, comprobar el cierre del contexto. Cerrar sesión y verificar que otra apertura no la recupera. Probar cámara y alternativa manual. | W-ID-01, W-ID-02, W-OPS-01 |
| A-03 · Taller | Docente con cupo, tallerista y dos estudiantes. | Convocar, seleccionar, agendar, inscribir y registrar una asistencia por QR y otra por código. La lista docente refleja las mismas cuentas. | W-TAL-01, W-AFO-01, W-ASI-01 |
| A-04 · Evidencia | Participantes con asistencia y recompensa configurada. | Entregar, devolver con comentario, corregir y aprobar. La foto queda restringida y hay un único abono financiado por el cupo. | W-EVI-01, W-EVI-02, W-PNT-01, W-CUP-01 |
| A-05 · Meta y nota | Meta verificada, regla y nota base simulada. | Convertir Coins, solicitar un canje aprobado y otro rechazado. Comprobar elegibilidad, reserva, consumo o devolución y nota simulada. | W-MET-01, W-WAL-01, W-NOT-01, W-NOT-02 |
| A-06 · Pago y red | Dos estudiantes en dispositivos distintos. | Cobrar y pagar por QR o código, recuperar el comprobante y repetir su consulta. Cambiar de red durante una confirmación y consultar el resultado antes de otro intento. Verificar un solo descuento. | W-PAG-01, W-WAL-01, W-RED-01, W-RED-02 |
| A-07 · Ardy | Estudiante con prendas y saldo de prueba. | Editar, guardar, abrir 3D, girar y volver a 2D. Interrumpir una nuez tras dos toques y retomarla. El tercer toque entrega una única prenda que puede equiparse. | W-NUE-01, W-RAN-01 |
| A-08 · Comunidad | Autor, otra cuenta, organizador y moderador. | Filtrar el feed, abrir sus recursos, cambiar la visibilidad del perfil y reportar y ocultar una foto. La comunidad deja de acceder al recurso restringido. | W-PER-01, W-SOC-01, W-FED-01 |
| A-09 · Torneo | Organizador y cuatro estudiantes. | Formar y aceptar dos parejas, publicar el cuadro y registrar una final. Ambos integrantes figuran como campeones. Confirmar el espacio por el canal institucional. | W-TOR-01, W-PAR-01 |
| A-10 · Agenda y avisos | Taller futuro con inscritos. | Reprogramar y cancelar con motivo. Abrir el taller desde un aviso, marcar los actuales como leídos y comprobar que un aviso posterior sigue pendiente. | W-AVI-01, W-AFO-01 |
| A-11 · Evaluación | Administración y resultados ficticios conocidos. | Consultar fechas y semanas y exportar CSV. Comparar los conteos con los registros del recorrido y verificar que otro rol no obtiene el informe. | W-INF-01 |
| A-12 · Recuperación | Responsable técnico y entorno separado. | Verificar el respaldo y restaurarlo en una base distinta. Registrar versión, esquema, datos de control y resultado de las consultas. | W-OPS-01 |

## Ficha para cada ejecución

Copiar esta ficha por caso y por dispositivo cuando cambie el entorno. Usar los estados Pendiente, En ejecución, Aprobado, Falló o Bloqueado. Un caso bloqueado registra qué condición impide ejecutarlo y quién puede resolverla.

| Campo | Registro |
| --- | --- |
| Caso y requisitos | |
| Fecha, hora y zona | |
| Versión de aplicación y revisión | |
| Entorno y URL | |
| Dispositivo, sistema y navegador | |
| Equipo físico o emulado | |
| Roles e identificadores de cuentas de prueba | |
| Responsable de observar y ejecutar | |
| Precondiciones y datos de control | |
| Resultado esperado | |
| Resultado observado | |
| Estado | Pendiente |
| Evidencia o referencia de operación | |
| Incidencia relacionada | |
| Repetición, fecha y resultado | |

Las observaciones de demo ya disponibles están en el [registro de verificación](verificacion-del-plan.md) y la bitácora de entregas. La aceptación institucional se documenta con la ficha y el [protocolo de evaluación](protocolo-de-evaluacion.md). La [guía por rol](manual-del-piloto.md) reúne los pasos de uso.
