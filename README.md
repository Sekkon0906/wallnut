# Wallnut

Una web instalable para la comunidad de la Universidad de Ibagué y un proyecto Android que usa la misma interfaz mediante Capacitor.

El piloto está desplegado en [Railway](https://wallnut-production.up.railway.app). La [guía de despliegue](docs/despliegue-del-piloto.md) explica cómo configurar y activar el acceso institucional.

El [plan de desarrollo y arquitectura](docs/plan-de-desarrollo-y-arquitectura.md) describe qué está implementado y qué se necesita para cerrar el piloto. La [guía de continuidad](docs/continuidad-del-proyecto.md) reúne las referencias y el registro para retomar tareas entre sesiones.

Los APK y paquetes de cada hito están en [Releases](https://github.com/Sekkon0906/wallnut/releases).

La [guía de despliegue del piloto](docs/despliegue-del-piloto.md) incluye el arranque con Compose y la restauración de prueba de PostgreSQL.

## Funciones disponibles

- Acceso institucional con Google Workspace, cuentas únicas y permisos por rol.
- La vista **Comunidad → Todo** reúne publicaciones, eventos y convocatorias por fecha. Permite filtrar por procedencia y abrir cada recurso con sus acciones disponibles.
- Administración habilita a docentes y asigna grupos. Docentes y administración confirman matrículas.
- El docente publica una convocatoria. El estudiante envía una propuesta y puede adjuntar un enlace. El docente puede aprobar una postulación por convocatoria.
- El estudiante consulta el estado en Comunidad o en Mis postulaciones.
- El docente o el tallerista aprobado programa el taller y define el lugar, el horario y los cupos. Los estudiantes se inscriben en Agenda y pueden liberar su cupo antes del inicio.
- Durante el taller, el docente o el tallerista genera un QR y un código manual con vigencia de hasta cinco minutos. El estudiante inscrito usa cualquiera de los dos para registrar su asistencia una sola vez.
- Después de registrar asistencia, el estudiante entrega una foto y un texto. El tallerista aprobado puede entregar su evidencia desde el inicio del taller. El docente aprueba la entrega o la devuelve con una observación para que el autor la corrija.
- La Agenda conserva los talleres anteriores para consultar y dar seguimiento a las evidencias.
- Antes del inicio, el docente o tallerista asignado puede reprogramar el taller sin perder inscripciones. El docente o Administración puede cancelarlo. La agenda conserva el estado y el motivo del cambio.
- Administración asigna un cupo de Ardi Points por docente. El docente configura cuánto otorga por cada evidencia aprobada de un asistente o del tallerista.
- Una meta académica verificada por el docente otorga Ardi Coins. El estudiante puede usar los Coins para canjear Ardi Points desde el cupo docente. Cada movimiento conserva el taller y la materia de origen.
- El docente configura el canje académico del grupo con una equivalencia en Points, un tope por corte, un mínimo opcional y los grupos de origen que admite. La plataforma trabaja con notas simuladas.
- El estudiante matriculado puede solicitar un ajuste con Points compatibles. La solicitud reserva el saldo hasta que el docente decide. Al aprobarla, se descuentan los Points y se actualiza la nota simulada. Al rechazarla, se libera la reserva y el estudiante ve el motivo.
- En **Mi Ardy**, cada estudiante puede guardar una ardilla 2D con altura, complexión, pelaje, cola, prendas y accesorios personalizables.
- El ranking suma Points acreditados por evidencias de participación. Los canjes de Coins y los ajustes de nota quedan fuera del cálculo. Cada estudiante decide si muestra su nombre y su Ardy en la clasificación.
- Al recargar la pestaña, Wallnut verifica la sesión y abre el espacio del rol correspondiente. Administración entra directamente a la gestión académica.
- El estudiante puede indicar su carrera, aplicar una apariencia inicial por área y adquirir accesorios en la tienda de Ardy con Coins.
- La tienda ofrece nueces sorpresa que se abren con tres toques y desbloquean prendas para el armario de Ardy.
- La tarjeta virtual permite cobrar y pagar Ardi Coins entre estudiantes por QR o código manual. El color se guarda en ese navegador o app. Las transacciones aparecen en ambas billeteras.
- En Comunidad se publican talleres, encuentros y torneos de estudiantes, docentes y administración. Los estudiantes pueden inscribirse o liberar su cupo antes del inicio.
- Cada estudiante puede crear un perfil del campus con su nombre, presentación y Ardy. El perfil es privado al empezar. Si se activa, otros usuarios de Wallnut pueden abrirlo desde los eventos de ese estudiante. La carrera se muestra solo si el titular lo elige.
- Comunidad permite filtrar eventos, publicaciones y convocatorias. Los estudiantes pueden compartir una foto o texto, editar sus publicaciones y reportar contenido. Administración revisa los reportes y puede ocultar la publicación.
- Los torneos individuales admiten un cuadro de eliminación directa. El organizador genera el cuadro con los inscritos y registra ganadores y marcadores. Cada ganador avanza a la ronda correspondiente.
- Los torneos por parejas admiten invitaciones entre estudiantes inscritos. Al confirmar, ambos entran como una pareja. El cuadro conserva los dos nombres y avanza a la pareja ganadora.
- **Ayuda de Ardi** permite elegir un tema o escribir una pregunta en español. Las respuestas se basan en las funciones de Wallnut y ofrecen accesos según el rol.

La [verificación del plan](docs/verificacion-del-plan.md) resume lo entregado y los recorridos pendientes en el entorno institucional.

Los **Ardi Coins** son unidades de uso interno sin valor monetario. El servidor administra los saldos y registra las operaciones en PostgreSQL. Los **Ardi Points** mantienen su origen académico y sus propias reglas de canje.

Wallnut guarda las fotos como JPEG en PostgreSQL. La descarga requiere una sesión del autor de la entrega o del docente asignado al grupo. La plataforma recibe JPG, PNG y WebP de hasta 8 MiB.

## Probar en Windows con datos ficticios

Requisitos: Python 3.11+, Node.js 22.12+ y PostgreSQL 17. Si se dispone de Docker, `docker compose up -d` desde la raíz inicia la base local `wallnut_demo`.

Terminal 1, desde la carpeta `api`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DATABASE_URL = 'postgresql://wallnut:wallnut_local@127.0.0.1:5432/wallnut_demo'
.\.venv\Scripts\python.exe -m wallnut.demo
```

Terminal 2, desde la carpeta `web`:

```powershell
npm ci
$env:VITE_DEMO = 'true'
npm run dev -- --strictPort
```

Abre [Wallnut local](http://127.0.0.1:5173). Entra como docente para publicar, como estudiante para postularte y otra vez como docente para seleccionar al tallerista. La cuenta ficticia de la estudiante para probar matrículas es `maria.piloto@estudiantesunibague.edu.co`. La demostración está limitada a la base `wallnut_demo` y se sirve en la máquina local.

### Probar agenda, asistencia y evidencia

1. Entra como docente y abre **Agenda**. La demo incluye el **Taller de series y convergencia** activo, con María ya inscrita. Genera el código de asistencia y cópialo.
2. Entra como estudiante, abre el mismo taller y registra la asistencia con el código. En un celular con cámara también puedes escanear el QR mostrado en otro dispositivo.
3. Adjunta una foto de un ejercicio y escribe qué trabajaste o dónde tuviste dificultades. Envía la evidencia.
4. Vuelve a entrar como docente y revisa la entrega desde el taller. Puedes aprobarla o devolverla con un comentario. Si la devuelves, entra de nuevo como estudiante para probar la corrección y el reenvío.

Para probar la programación y la inscripción, usa una convocatoria con un tallerista ya seleccionado y programa el inicio para una hora futura. Puedes inscribirte o cancelar la inscripción hasta que comience el taller. El escáner del navegador requiere permiso de cámara y un sitio HTTPS o una dirección local como `localhost`. El código manual también funciona si el dispositivo no tiene cámara o si deniegas el permiso.

Si el taller de ejemplo ya terminó, reinicia la API de demostración para abrir uno nuevo. Las entregas del taller anterior siguen en la Agenda.

### Probar la billetera

Desde Administración, abre **Ver movimientos** junto al cupo de un docente. El historial muestra asignaciones, recompensas y conversiones a Points, con totales y referencias de cada operación. Asigna Points y confirma que se actualizan el saldo y el historial. El docente puede abrir el mismo detalle desde **Mis grupos → Mi cupo docente**.

El **Taller de series y convergencia** viene configurado con un cupo inicial de 1.000 Points para la docente. En una base nueva, la billetera de María empieza en cero.

1. Registra asistencia como en el recorrido anterior. Como estudiante, envía una foto y un texto que expliquen qué criterio de convergencia aplicaste y por qué.
2. Como docente, abre **Agenda** y elige **Aprobar evidencia** en la entrega. La aprobación acredita **20 Ardi Points** desde el cupo si hay saldo suficiente. La recompensa de ejemplo para el tallerista es de **35 Points**.
3. En la evidencia aprobada, comprueba que se cumplió la meta y elige **Verificar meta y otorgar Coins**. Esta acción otorga **10 Ardi Coins** una sola vez. Una evidencia puede estar aprobada y tener la meta aún por verificar.
4. Como estudiante, abre **Billetera** y elige **Canjear por Points** para convertir **8 Coins en 5 Points**. Si partías de cero, el saldo queda en **25 Points y 2 Coins**. La aprobación y el canje consumen **25 Points** del cupo de la docente.

Si falta cupo, usa **Administración → Cupos docentes → Asignar Points**. La docente puede elegir **Acreditar Points** en la evidencia aprobada y el estudiante puede reintentar el canje desde la billetera. Reiniciar la demo conserva los movimientos y el saldo ya consumido.

En otro taller, el docente puede elegir **Configurar recompensas** en la agenda para definir los Points. Para habilitar el canje, también define qué debe cumplir el estudiante, cuántos Coins otorga la meta y cuántos Points se reciben por el costo en Coins. La regla del taller se fija con el primer movimiento de la billetera.

### Probar el canje académico simulado

María tiene una matrícula confirmada en **Cálculo III** y una nota base simulada de **3,700**. La demo configura un corte de práctica que acepta Points del mismo grupo. Cada **10 Points** aumentan **0,100** la nota y el tope acumulado es **+0,200**.

1. Completa el recorrido de la billetera para obtener Points del **Taller de series y convergencia**. Con la aprobación de una evidencia se obtienen 20 Points, y con el canje de Coins del ejemplo se llega a 25.
2. Como estudiante, abre **Mis grupos → Cálculo III → Canje académico**. También puedes entrar desde **Billetera → Ver canjes académicos**. Consulta la nota simulada y los Points disponibles para el grupo. Elige un paso de **+0,100** y pulsa **Solicitar ajuste**.
3. Abre **Billetera** para comprobar que se reservan 10 Points mientras la solicitud está pendiente. Si el saldo era de 25, quedan 15 Points disponibles para otro uso.
4. Como docente, abre **Canje académico** en el mismo grupo. Elige **Aprobar ajuste** para consumir los 10 Points y actualizar la nota a **3,800**. Si prefieres rechazar la solicitud, elige **Rechazar ajuste**, escribe un motivo y pulsa **Confirmar rechazo** para liberar los Points.

Para probar tus propias reglas, usa **Guardar regla** y **Guardar nota** en la vista docente. Para usar Points de otro grupo, el docente del taller debe permitirlo en **Uso académico de los Points**, y el docente del grupo de destino debe admitir ese origen en su regla. La nota se calcula en milésimas, con un máximo de 5,000. Los resultados de la demo son ficticios y quedan en Wallnut.

### Probar Mi Ardy y el ranking

1. Entra como estudiante y abre **Mi Ardy**. Cambia el pelaje o prueba distintos accesorios. La vista previa se actualiza al instante.
2. Si quieres aparecer en la clasificación, activa **Mostrar mi nombre y mi Ardy en el ranking** y elige **Guardar mi Ardy**. La opción viene desactivada.
3. Abre **Ranking** después de recibir una recompensa por una evidencia aprobada. La clasificación ordena primero por Points ganados y luego por actividades verificadas. Para ocultar tu perfil, desactiva la opción y guarda de nuevo.

### Probar la tarjeta, la tienda y los eventos

En Billetera, **Solicitudes recientes** permite retomar un cobro después de recargar y consultar sus pagos. Genera un cobro como Mateo, recarga y abre **Ver solicitud** para recuperar el mismo QR. Usa su código para pagar como María. Ambas cuentas pueden consultar el resultado y la fecha del pago. Ante una confirmación interrumpida, **Consultar resultado** recupera el estado desde el servidor.

1. Consigue Ardi Coins como María siguiendo los primeros tres pasos del recorrido de la billetera. En otra pestaña entra como **Mateo · estudiante de prueba**.
2. Como Mateo, abre **Billetera → Recibir Coins**. Elige la cantidad y genera el QR. Cada solicitud vence en cinco minutos y admite un solo pago.
3. Como María, abre **Billetera → Pagar con QR**. Escanea el QR que muestra el otro dispositivo o pega el código manual. Revisa el nombre y la cantidad antes de pulsar **Confirmar pago**. Como Mateo, elige **Consultar estado** para actualizar el saldo.
4. En **Mi Ardy**, escribe tu carrera y prueba una apariencia inicial. Si tienes Coins, puedes comprar una gorra dorada o una chaqueta violeta. Tras probarla, elige **Guardar mi Ardy** para equiparla.
5. En **Comunidad → Crear evento**, publica un torneo, taller o encuentro con lugar, inicio en hora de Ibagué y cupos. En la segunda cuenta, comprueba que aparece en el feed e inscríbete. Las publicaciones identifican si vienen de estudiantes o del personal universitario.

### Abrir una nuez sorpresa

1. Obtén Ardi Coins con una meta verificada y abre **Mi Ardy → Tienda de Ardy**. La nuez cuesta **4 Coins**.
2. Elige **Comprar nuez** y confirma. La pantalla de apertura recibe tres toques. Puedes tocar la nuez o activar su botón con el teclado. El primer toque dibuja una grieta, el segundo separa el cascarón y el tercero revela la prenda.
3. El brillo es blanco azulado para **Normal**, menta para **Especial**, violeta para **Épica** y dorado para **Legendaria**. Al cerrar, puedes volver con **Continuar apertura**. El premio se guarda en el armario al tercer toque.
4. Elige **Probar en Mi Ardy** para previsualizar la prenda y **Guardar mi Ardy** para equiparla. Puedes ver la última prenda en **Ver último premio**.

La colección del piloto tiene ocho prendas, dos por rareza, y cada nuez desbloquea una diferente. Las probabilidades iniciales son 60 % Normal, 25 % Especial, 12 % Épica y 3 % Legendaria. Cuando se completan las prendas de una rareza, su peso se excluye y se recalculan las proporciones de las restantes. La tienda muestra las probabilidades vigentes antes de comprar.

### Probar los perfiles del campus

1. Como María, abre **Mi Ardy → Mi perfil del campus**. Escribe una presentación. Activa **Mostrar mi perfil en el campus** y guarda. Puedes elegir si compartes la carrera que guardaste en Mi Ardy.
2. Publica un evento desde **Comunidad**. Entra en otra pestaña como Mateo y abre el perfil desde el nombre de María en la tarjeta del evento.
3. Desactiva la visibilidad y guarda como María. Al volver a cargar los eventos, Mateo vuelve a ver el nombre del organizador sin acceso al perfil.

### Probar publicaciones y el cuadro de un torneo

Para revisar el feed, abre **Comunidad → Todo**, selecciona una procedencia y abre una tarjeta. **Volver al feed** recupera la lista actualizada. Si hay más contenido, **Ver más contenido** continúa desde la última tarjeta cargada.

1. Entra como estudiante y abre **Comunidad → Publicaciones**. Escribe un texto, adjunta una foto o combina ambos. Revisa la tarjeta que ve la comunidad y prueba la edición.
2. Entra con la segunda cuenta estudiantil y reporta una publicación de prueba. Entra como administración y abre **Comunidad → Publicaciones** para revisar el reporte y probar la moderación. Las fotos del feed requieren una sesión de Wallnut. Se guardan normalizadas y el enlace deja de servir cuando se oculta el contenido para la comunidad.
3. Publica un evento de tipo **Torneo** e inscribe dos estudiantes desde sus cuentas. Como organizador, abre **Ver cuadro** y confirma **Generar cuadro**. A partir de ese momento se cierran las inscripciones.
4. En el cuadro, elige **Registrar resultado**, selecciona el ganador y añade un marcador si hace falta. Con más de dos participantes, revisa que el resultado llene el cruce de la siguiente ronda. Al terminar la final se muestra el campeón.

### Probar un torneo por parejas

1. Como docente, crea en **Comunidad → Eventos** un torneo futuro con modalidad **Por parejas** y al menos cuatro cupos. Los cupos cuentan estudiantes.
2. Inscribe cuatro estudiantes. La demo incluye a María, Mateo, Camila y Julián. Las dos últimas cuentas se abren desde **Más cuentas para torneos**.
3. Como María, abre **Ver cuadro → Mi pareja**, elige a Mateo y envía la invitación. Como Mateo, abre la misma vista y elige **Aceptar**. Forma la segunda pareja con Camila y Julián.
4. Como organizador, abre el cuadro y elige **Generar cuadro**. El registro se cierra y avanzan las parejas confirmadas. En la final, registra el resultado y comprueba que se muestran los dos integrantes de la pareja campeona.

### Probar Ayuda de Ardi

1. Inicia sesión y abre **Ayuda de Ardi** desde cualquier sección.
2. Como estudiante, prueba «¿Cómo canjeo Coins por Points?» y sigue el botón a **Billetera**.
3. Como docente, elige **Talleres y convocatorias** para ir a la vista de convocatorias. Como administración, elige **Publicaciones y reportes** para ir a la sección desde donde se revisan los reportes.

El asistente usa guías de Wallnut y adapta las acciones a la cuenta. La conversación se conserva en la pantalla mientras está abierta.

### Probar cambios en la agenda

1. Agenda un taller futuro desde **Comunidad → Convocatorias** e inscríbete desde una cuenta estudiantil.
2. Como docente o tallerista asignado, entra en **Agenda → Reprogramar**. Cambia el horario o lugar e indica el motivo. Como estudiante, abre **Mis talleres** y verifica el nuevo horario y tu inscripción.
3. Como docente asignado o Administración, elige **Cancelar taller** e indica el motivo. La ficha se conserva en **Cancelados** y la inscripción permanece en el historial. La cancelación cierra los cupos, el QR y las evidencias de ese taller.

### Consultar el historial completo de la billetera

Como estudiante, abre **Billetera → Movimientos**. El resumen muestra los ingresos, gastos y Points reservados de toda tu cuenta. Usa **Points** o **Coins** para filtrar la lista y **Ver movimientos anteriores** para continuar con el historial. Un canje de Coins a Points aparece en ambos filtros. Abre **Referencia** para identificar una operación y **Actualizar movimientos** para consultar las más recientes.

Un canje académico pendiente reserva los Points. Si el docente lo aprueba aparece como gasto; si lo rechaza, se libera la reserva y puedes consultar el motivo en **Canjes académicos**. El historial es privado para la propia cuenta estudiantil.

### Probar los avisos

1. Agenda un taller futuro e inscribe a una cuenta estudiantil. Reprográmalo desde el docente o tallerista asignado. Abre **Avisos** desde la cuenta inscrita y comprueba el nuevo aviso.
2. Pulsa **Ver taller**. La agenda enfoca ese taller y el aviso queda leído. **Solo sin leer** muestra lo que aún tienes pendiente.
3. Entrega una evidencia y revísala desde el docente. Las entregas y correcciones generan avisos para su destinatario. Prueba también una solicitud de canje y su aprobación o rechazo.
4. **Marcar todos como leídos** conserva los avisos que lleguen después de la consulta actual. **Ver avisos anteriores** continúa con el historial.

El contador se consulta al entrar, al volver a la pestaña y cada minuto mientras la página está visible. **Actualizar avisos** permite consultarlos en el momento. Los avisos se conservan en la cuenta al cerrar sesión y se crean al realizar nuevos cambios de agenda, evidencias y canjes.

## Probar el APK de demostración

Inicia primero la API y la web local como se explica arriba. Con un emulador Android abierto o un teléfono de desarrollo conectado por USB:

```powershell
adb reverse tcp:5173 tcp:5173
adb install -r Wallnut-Android-hito21-demo.apk
```

El APK de demostración abre la web local a través del túnel USB y usa las cuentas ficticias. Para recompilarlo, ejecuta desde `web`:

```powershell
$env:CAPACITOR_LOCAL_DEMO = 'true'
npm run android:sync
cd android
.\gradlew.bat assembleDebug
```

El APK está en `web/android/app/build/outputs/apk/debug/app-debug.apk`. Para compilar una app Android con la web empaquetada, elimina `CAPACITOR_LOCAL_DEMO` de tu sesión y sincroniza de nuevo. Android requiere un JDK 21 y el SDK 36 para este proyecto.

## Configurar el acceso institucional

1. Configura un cliente OAuth web para la URL donde se sirve Wallnut. Usa su ID en `VITE_GOOGLE_CLIENT_ID` para la interfaz y en `GOOGLE_CLIENT_IDS` para la API. El servidor verifica la firma, la audiencia del token, el dominio administrado y el correo verificado.
2. Configura `DATABASE_URL` para una base dedicada al piloto. Desde `api`, ejecuta `python -m wallnut.database` y luego `python -m uvicorn wallnut.main:app`. La cuenta de personal debe iniciar sesión primero. Ejecuta `python -m wallnut.administration correo@unibague.edu.co` para habilitar a la primera persona administradora.
3. Para la web, sirve el contenido de `web/dist` mediante HTTPS y dirige `/v1` a la API. Si usas un proxy inverso, configura un límite de solicitud de 9 MiB para admitir la foto de 8 MiB y los campos del formulario. `npm run build` genera los archivos instalables. En iPhone se puede añadir el sitio a la pantalla de inicio desde Safari.
4. Para Android, configura un cliente OAuth Android con el ID de paquete `dev.wallnut.campus` y la huella SHA-1 del certificado usado. Usa `VITE_API_URL` con la dirección HTTPS de la API y agrega `https://localhost` a `WEB_ORIGINS` para el origen de Capacitor. Sigue la [guía de Google en Android de Capgo](https://capgo.app/docs/plugins/social-login/google/android/).

La compilación para el piloto se genera con `VITE_DEMO` desactivado y con el acceso institucional configurado.

## Verificación

Desde `api`, instala `requirements-dev.txt`, define `TEST_DATABASE_URL` con una base PostgreSQL para pruebas y ejecuta `python -m pytest -q`. Las pruebas usan un esquema temporal y credenciales simuladas. Cubren talleres, evidencias, billetera, canje académico, ranking, compras, pagos, inscripciones y el cobro único y la apertura de nueces. Desde `web` ejecuta `npm run check` para verificar la interfaz.

La imagen de Ardy se creó a partir del boceto del proyecto con esta indicación: aislar y redibujar la ardilla naranja como recorte transparente, conservando la cola en espiral, el mechón central, el hocico crema, las gafas redondas y el buzo azul.
