# Wallnut · Continuidad del proyecto

**Punto de partida para la siguiente ronda · 18 de noviembre de 2026**

## Referencias compartidas

- La rama `main` de [Wallnut](https://github.com/Sekkon0906/wallnut) contiene el producto activo. La versión [0.19.0](https://github.com/Sekkon0906/wallnut/releases/tag/v0.19.0) añade el historial del cupo docente y la comprobación entre sus asignaciones, acreditaciones y saldo. La revisión desplegada se consulta en Railway. El primer prototipo está en [archivo/prototipo-flutter](https://github.com/Sekkon0906/wallnut/tree/archivo/prototipo-flutter).
- El [plan actualizado](plan-de-desarrollo-y-arquitectura.md) concentra el alcance, los pendientes y las condiciones de cierre. El [registro de verificación](verificacion-del-plan.md) contiene los recorridos y el [manual de despliegue](despliegue-del-piloto.md) explica Railway y la conexión con PostgreSQL.
- La [bitácora de Obsidian](https://github.com/Sekkon0906/boveda-obsidian/tree/main/Proyectos/Wallnut) reúne las decisiones, las entregas y las copias del plan y la guía. Los detalles de implementación y cambios de código se versionan en el repositorio de Wallnut.

## Cómo retomar una tarea

1. Leer la instrucción del equipo de grado y localizar su etapa y criterio de cierre en el plan. Registrar la revisión base y los módulos afectados.
2. Revisar el estado del repositorio antes de editar. Para trabajo simultáneo, usar ramas independientes y acordar los archivos o módulos que toma cada sesión. Si una tarea cambia una ruta, un esquema o un tipo compartido, acordar el contrato con quien trabaje sobre ese mismo flujo.
3. Usar las cuentas de demostración y una base de pruebas para reproducir el recorrido. Las instrucciones de arranque y comandos están en el [README](../README.md). Los cambios de UI se comprueban con `npm run check`; los de API con `python -m pytest -q` y una `TEST_DATABASE_URL` dedicada. Añadir un caso de regresión cuando una regla o un fallo del usuario lo requiera.
4. Dejar la revisión o el enlace al cambio, los resultados observados y la decisión pendiente en la bitácora al entregar la tarea. Los cambios de roles, saldos, notas y datos privados necesitan revisión del recorrido de extremo a extremo y de los permisos de API.

## Dos líneas de trabajo posibles

La asignación se decide al recibir las próximas instrucciones. La división propuesta para trabajar con Codex y Claude permite que una sesión prepare despliegue, API y datos, y la otra trabaje en experiencia móvil, Comunidad y pruebas con usuarios. Los dos integrantes del proyecto deciden los cambios de alcance y revisan los contratos que conectan ambas líneas.

| Línea | Punto de entrada | Dependencias compartidas |
| --- | --- | --- |
| **Acceso y datos** | `api/wallnut/identity.py`, `api/wallnut/pilot.py`, `database/` y configuración Railway. | ID OAuth web, rol inicial de administración y contrato de sesión. Criterios de procedencia, topes y reservas antes de ajustar economía. |
| **Experiencia y validación** | `web/src/Community.vue`, `web/src/SignIn.vue`, agendas, billetera y recursos de la PWA. | `web/src/client.ts` para contratos compartidos. Datos ficticios para el feed y permisos. Dispositivos físicos para el ensayo con cuentas institucionales. |

## Registro breve para cada entrega

| Campo | Qué anotar |
| --- | --- |
| Tarea y base | Resultado esperado, rama o revisión inicial y responsable. |
| Cambios | Archivos, rutas o migraciones que afecten otro módulo. |
| Comprobación | Comando o recorrido, resultado y entorno. |
| Continuación | Decisión abierta, dependencia o siguiente paso concreto. |

El primer punto pendiente es registrar el cliente OAuth web y habilitar el acceso en la [web de Railway](https://wallnut-production.up.railway.app). El próximo recorrido es validar acceso, taller, pago y canje simulado con cuentas institucionales en equipos físicos. El feed y la recuperación de pagos se pueden ensayar con la demo local. Compartir el ID público de Google es suficiente para la configuración descrita en la guía. Las contraseñas, credenciales de Railway y datos institucionales se conservan en su entorno autorizado.
