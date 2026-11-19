# Guía del piloto de Wallnut

**Aplicación 0.22.0 · Universidad de Ibagué · 18 de noviembre de 2026**

Wallnut reúne actividades del campus, apoyo académico, una billetera interna y la personalización de Ardy. Ardi Points y Ardi Coins son unidades internas sin valor monetario. Los canjes académicos de este piloto usan notas simuladas.

Esta guía describe las funciones disponibles. El acceso institucional de la [web de Railway](https://wallnut-production.up.railway.app) está pendiente de configurar Google OAuth. El [README](../README.md) explica cómo usar la demostración con cuentas ficticias y el APK local. La [matriz de aceptación](matriz-de-aceptacion.md) distingue las comprobaciones automáticas de los ensayos institucionales pendientes.

## Entrar y orientarse

En el entorno institucional, entra con tu cuenta de Google de la Universidad. Wallnut verifica el correo y presenta las secciones de tu rol. Si falta un grupo o una habilitación docente, solicita al responsable del piloto que revise la asignación de tu cuenta.

La web se puede abrir desde el navegador o desde el acceso que instales en la pantalla de inicio. En iPhone el recorrido previsto usa Safari. El APK descargable actual es de demostración y necesita el servidor local descrito en el README. La instalación y el acceso institucional en teléfonos físicos forman parte del ensayo pendiente.

| Sección | Para qué sirve |
| --- | --- |
| Comunidad | Descubrir eventos, publicaciones y convocatorias. Filtrar procedencia y abrir cada recurso. |
| Agenda | Inscribirse, consultar horarios de Colombia, registrar asistencia y gestionar un taller asignado. |
| Mis grupos | Consultar grupos y abrir Canje académico. El docente también consulta su cupo y confirma matrículas. |
| Billetera | Consultar saldos, recibir y pagar Coins, revisar movimientos y canjes por metas verificadas. |
| Mi Ardy | Personalizar la ardilla, revisar prendas y nueces y elegir la visibilidad del perfil y del ranking. |
| Avisos | Consultar cambios de agenda y actividad académica de la propia cuenta. |
| Evaluación | Consultar y exportar indicadores agregados desde Administración. |

Las funciones visibles dependen del rol. **Ayuda de Ardi** ofrece guías y accesos a las secciones de la cuenta.

## Estudiantes

### Encontrar una actividad y asistir

1. Abre **Comunidad → Todo**. Puedes filtrar Universidad o Estudiantes. Abre una tarjeta para consultar su evento, publicación o convocatoria.
2. En **Agenda**, revisa fecha, lugar y cupos. Usa **Inscribirme** en un taller futuro. **Mis talleres** reúne tus inscripciones y las actividades donde eres tallerista.
3. Durante el taller, abre **Registrar asistencia**. Escanea el QR o introduce el código temporal que presenta el docente o tallerista. Si la cámara no está disponible, usa el código manual.
4. Si se cambia o cancela la actividad, consulta **Avisos**. **Ver taller** abre y enfoca la ficha correspondiente. El motivo y el estado se conservan en Agenda.

El registro de asistencia corresponde a tu cuenta y al taller del código. Un código vencido requiere que el responsable genere uno nuevo.

### Entregar evidencia y recibir recompensas

1. Después de registrar asistencia, abre **Mi evidencia** en el taller.
2. Adjunta una foto JPG, PNG o WebP dentro del límite que muestra el formulario. Explica tu trabajo en **¿Qué hiciste durante el taller?** y pulsa **Enviar evidencia**.
3. Revisa el resultado desde la misma ficha o desde un aviso. Si aparece una devolución, lee la retroalimentación, corrige la foto y el texto y usa **Reenviar evidencia**.
4. Una evidencia aprobada muestra los Points acreditados. Si indica **Points pendientes**, el docente debe completar la acreditación con cupo disponible.
5. Si el taller tiene una meta de Coins, el docente debe verificarla. Después, en **Billetera → Canjes por metas verificadas**, puedes consultar el coste y solicitar el canje por Points.

La foto y reflexión académicas se consultan desde tu cuenta y desde el docente asignado. El rol de tallerista permite gestionar su actividad y entregar su propia evidencia; las revisiones de evidencias de otros estudiantes corresponden al docente.

### Postularse como tallerista

En **Comunidad → Convocatorias**, abre una convocatoria disponible y pulsa **Postularme**. Explica cómo orientarías el taller y añade el enlace de sustento cuando corresponda. El docente revisa las postulaciones y selecciona a una persona.

Si te seleccionan, la convocatoria permite **Agendar taller**. En la actividad asignada puedes gestionar la emisión del QR y reprogramar antes del inicio. La cancelación del taller corresponde al docente asignado o a Administración.

### Usar la billetera y la tarjeta

Para recibir Coins, abre **Billetera → Recibir Coins**, indica la cantidad y genera el QR de cobro. Comparte el QR o su código con quien vaya a pagar. Para pagar, usa **Pagar con QR**, escanea o introduce el código y revisa destinatario, cantidad y vencimiento antes de confirmar.

**Solicitudes recientes** permite recuperar un cobro y abrir un comprobante. Si una confirmación se interrumpe, usa **Consultar resultado** antes de volver a intentar el pago.

En **Movimientos**, los filtros **Todos**, **Points** y **Coins** cambian la lista. El resumen siempre corresponde a la cuenta completa y separa los Points reservados. **Referencia** identifica una operación y **Ver movimientos anteriores** continúa con el historial. Un canje de Coins a Points aparece en ambos filtros.

### Solicitar un canje académico simulado

1. En **Mis grupos**, abre **Canje académico** del grupo donde tienes matrícula confirmada.
2. Revisa la evaluación simulada, la nota base, los Points elegibles, el incremento y el tope definidos por el docente.
3. Indica cuántos incrementos solicitas y revisa la mejora y el coste antes de enviar.
4. La solicitud pendiente reserva sus Points. La aprobación consume esa reserva y actualiza la nota simulada. El rechazo libera la reserva y conserva su motivo.

La elegibilidad depende de la configuración del grupo, del origen de los Points y de la nota base simulada. El piloto aún requiere acordar con el tutor la medida académica y la procedencia de Coins que se aceptarán en el ensayo institucional.

### Personalizar Ardy y elegir visibilidad

En **Mi Ardy**, completa tu carrera si quieres usar un estilo inicial y edita apariencia, ropa y accesorios. Las vistas 2D y 3D comparten la edición. **Guardar mi Ardy** conserva la apariencia elegida. Las prendas compradas u obtenidas de nueces aparecen en el armario para probarlas y equiparlas.

Antes de comprar una nuez, revisa las probabilidades vigentes. La apertura tiene tres toques y el tercero revela la prenda. Si sales antes, **Continuar apertura** permite retomarla. **Probar en Mi Ardy** lleva la prenda al editor; guarda la apariencia para equiparla.

**Mostrar mi nombre y mi Ardy en el ranking** controla tu participación voluntaria en esa clasificación. En **Mi perfil del campus**, puedes decidir si muestras el perfil y si compartes la carrera. Usa **Guardar perfil** para confirmar esas preferencias. Son controles independientes.

### Publicaciones, eventos y torneos

En Comunidad puedes crear una publicación con texto o foto y organizar un evento con lugar, fecha y cupos. Revisa las opciones de edición, retirada y reporte de cada recurso. La organización del espacio físico se confirma con el responsable institucional.

En un torneo por parejas, ambos estudiantes deben inscribirse. Uno invita y el otro acepta. El organizador publica el cuadro con las parejas confirmadas y registra los resultados. Quienes sigan sin pareja al publicar el cuadro quedan fuera de sus cruces.

## Docentes

### Preparar grupo, cupo y taller

1. Comprueba en **Mis grupos** los grupos que te asignaron. Confirma la matrícula con el correo institucional del estudiante cuando corresponda.
2. Consulta tu cupo en esa misma sección. **Ver movimientos** muestra las asignaciones de Administración, las acreditaciones por evidencia, las conversiones y el saldo disponible.
3. En **Comunidad → Convocatorias**, pulsa **Publicar convocatoria**. Selecciona el grupo y describe la actividad.
4. Usa **Revisar postulaciones**, selecciona al tallerista y agenda el taller. El tallerista seleccionado también puede agendarlo.
5. En **Agenda**, abre las recompensas de tu taller y configura **Points por asistir**, **Points para el tallerista** y **Uso académico de los Points**. Si procede, completa la meta, los Coins que entrega y su conversión. Pulsa **Guardar recompensas** antes de la primera acreditación o validación de meta.

Las reglas de recompensa que ya se usaron conservan sus valores. La opción de origen del taller y los grupos de origen aceptados por el grupo receptor determinan dónde se podrán usar esos Points.

### Asistencia, evidencia y cupo

Durante la actividad, **QR y código** presenta el registro temporal. **Ver inscritos** muestra nombres, asistencia y estado de evidencia para el docente asignado. Permite buscar y filtrar durante el taller.

En la revisión, abre la foto y reflexión. Usa **Aprobar evidencia** o **Devolver para corregir**. Una devolución necesita comentario. El estudiante recibe el aviso y puede reenviar su corrección. Revisa la versión actual antes de decidir.

Si una aprobación muestra **Points pendientes**, consulta tu cupo y gestiona una asignación cuando haga falta. Después usa **Acreditar Points** en esa evidencia. **Verificar meta y otorgar Coins** acredita la meta configurada. Los reintentos de estas acciones mantienen una sola acreditación.

### Regla de canje y decisiones

En **Mis grupos → Canje académico**, configura **Evaluación simulada**, **Points por incremento**, **Incremento de nota**, **Tope total de mejora**, el mínimo opcional y los grupos de origen aceptados. Registra la nota base simulada de cada estudiante matriculado.

Revisa **Solicitudes del grupo**. **Aprobar ajuste** consume los Points reservados; **Rechazar ajuste** requiere un motivo y los devuelve al saldo disponible. La interfaz conserva el historial. Las reglas y notas que tienen solicitudes activas conservan sus restricciones de edición.

### Cambios de agenda y avisos

Antes del inicio puedes reprogramar o cancelar un taller indicando un motivo. Los cupos deben alcanzar para las inscripciones ya confirmadas. La agenda conserva el horario anterior, el motivo y las inscripciones. Los participantes actuales reciben el aviso del cambio.

Las nuevas evidencias y solicitudes de canje aparecen en **Avisos**. Abre el recurso desde allí para revisar su estado vigente. Marcar el aviso como leído no decide la evidencia ni el canje.

## Administración

### Preparar las cuentas y grupos

La primera cuenta administradora se habilita con el procedimiento de la [guía de despliegue](despliegue-del-piloto.md). Una vez dentro, **Administración académica** permite habilitar docentes con **Asignar rol**, crear grupos y confirmar matrículas. La cuenta institucional debe haber entrado primero para que exista su registro.

Asigna Points al cupo docente y verifica la confirmación. **Ver movimientos** permite reconstruir cuánto se asignó, cuánto se acreditó y qué saldo queda. Si el resumen muestra una diferencia, conserva las referencias y comunícala al responsable técnico para su revisión.

### Moderar y operar el piloto

En **Comunidad → Publicaciones**, revisa los reportes y las acciones de moderación. Acuerda quién atenderá esa cola durante el ensayo y cómo se informarán sus decisiones. La revisión académica de fotos y notas pertenece a sus funciones docentes.

En **Evaluación**, selecciona 4, 8 o 12 semanas y una fecha de corte si la necesitas. **Consultar** actualiza el informe y **Descargar CSV** exporta esos mismos datos. Conserva la fecha de corte, la de generación y la zona horaria junto al resultado. El [protocolo de evaluación](protocolo-de-evaluacion.md) explica los denominadores y ofrece las plantillas para observación e incidencias.

La persona responsable del despliegue verifica respaldos y su recuperación en un entorno separado siguiendo la guía operativa. El equipo de grado completa los resultados de la matriz antes de dar por aceptado el piloto institucional.

## Recuperarse de una interrupción

Conserva la vista abierta si se pierde la conexión. **Comprobar conexión** consulta si el servicio está disponible y mantiene los campos de esa pantalla. Al volver, actualiza la sección y consulta el resultado de cualquier pago o envío interrumpido antes de repetirlo. Cambiar de sección o recargar puede descartar campos aún sin guardar.

Si Wallnut informa que la sesión terminó, vuelve a entrar con tu cuenta. Para registrar una incidencia, anota qué intentabas hacer, hora, versión, rol, dispositivo y la referencia de la operación si existe. La plantilla del protocolo permite conservar ese seguimiento sin copiar credenciales.
