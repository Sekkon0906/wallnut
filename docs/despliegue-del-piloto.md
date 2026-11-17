# Despliegue del piloto institucional

El piloto sirve la web instalable y la API desde el mismo origen. La app escucha en el servidor local y PostgreSQL queda en la red interna de Compose. El proxy institucional publica el servicio con un certificado HTTPS válido.

## Configurar y arrancar

1. Reserva un dominio de prueba y registra su origen HTTPS en el cliente OAuth web de Google Workspace. Confirma con el responsable institucional que las cuentas de prueba puedan usar el cliente.
2. Copia `.env.pilot.example` a `.env.pilot`. Define el origen, el identificador OAuth web y una contraseña exclusiva para la base. El mismo identificador OAuth configura el frontend y la API. Usa `WALLNUT_ANDROID_ORIGIN` cuando se prepare un APK con la interfaz empaquetada.
3. En el servidor con Docker y Compose ejecuta desde la raíz del repositorio:

```sh
docker compose --env-file .env.pilot -f compose.pilot.yaml up --build -d --wait
docker compose --env-file .env.pilot -f compose.pilot.yaml exec app python -m wallnut.pilot --check
```

4. Dirige el proxy HTTPS a `127.0.0.1:8080` o al puerto local que configuraste. Conserva las rutas `/v1`, `/manifest.webmanifest` y `/sw.js` e impón el límite de carga descrito en el README. Desde el dominio prueba la página de inicio y `/v1/ready`. Esta última ruta responde 200 cuando PostgreSQL tiene las migraciones y 503 cuando falta preparación.
5. Entra con la cuenta institucional que administrará el piloto y luego ejecuta, sustituyendo el correo de ejemplo:

```sh
docker compose --env-file .env.pilot -f compose.pilot.yaml exec app python -m wallnut.administration responsable@unibague.edu.co
```

El arranque aplica las migraciones de forma transaccional. El comando `--check` revisa la configuración, los archivos web y el estado del esquema sin modificarlos. Mantén `.env.pilot` y sus copias en el servidor. Para diagnóstico de Compose usa `docker compose --env-file .env.pilot -f compose.pilot.yaml config --quiet`, que valida el archivo sin imprimir los valores de configuración.

Documentación de referencia para [las variables de Compose](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/) y [el orden de arranque](https://docs.docker.com/compose/how-tos/startup-order/).

## Respaldo y restauración de prueba

Guarda el respaldo fuera del servidor y prueba su restauración en una base separada antes de cualquier actualización. Estos comandos usan el mismo contenedor únicamente para verificar una restauración con un nombre nuevo.

```sh
docker compose --env-file .env.pilot -f compose.pilot.yaml exec -T postgres pg_dump -U wallnut -Fc -f /tmp/wallnut-pilot.dump wallnut_pilot
docker compose --env-file .env.pilot -f compose.pilot.yaml cp postgres:/tmp/wallnut-pilot.dump ./wallnut-pilot.dump
docker compose --env-file .env.pilot -f compose.pilot.yaml exec -T postgres createdb -U wallnut wallnut_restauracion
docker compose --env-file .env.pilot -f compose.pilot.yaml exec -T postgres pg_restore -U wallnut --exit-on-error -d wallnut_restauracion /tmp/wallnut-pilot.dump
docker compose --env-file .env.pilot -f compose.pilot.yaml exec -T postgres psql -U wallnut -d wallnut_restauracion -c 'SELECT count(*) FROM migrations;'
```

Los respaldos pueden contener evidencias académicas y fotos. Limita su acceso a la persona responsable del piloto y aplica la retención acordada con la Universidad.

## Aceptación con cuentas y dispositivos

La verificación automática construye y arranca una instancia de prueba, comprueba la web y la API y ensaya una restauración de PostgreSQL. El siguiente paso es ejecutar la [validación institucional](verificacion-del-plan.md#validación-institucional) con cuentas autorizadas e iPhone y Android físicos. El APK descargable de demostración sigue el procedimiento local del README. Para un APK institucional prepara la configuración OAuth y el empaquetado descritos en el README.
