# Wallnut (Ardys)

Plataforma móvil para una institución universitaria. Digitaliza las actividades del campus (charlas, debates, laboratorios, eventos de la comunidad) y propone una nueva economía basada en **puntos positivos**: quien participa gana puntos, los guarda en su billetera y puede transferirlos o usarlos dentro de la comunidad.

> **Código:** el repositorio principal es privado y está en la organización [BBMC-S-S-A](https://github.com/BBMC-S-S-A) (`BBMC-S-S-A/Wallnut`). Este repositorio es la ficha pública del proyecto. El código completo se comparte bajo acuerdo.

## Qué hace

- **Actividades del campus:** cada actividad se publica en la app, y la asistencia se registra escaneando un código QR con la cámara del teléfono.
- **Economía de puntos positivos:** participar suma puntos. Cada usuario tiene saldo e historial de movimientos, y puede transferir puntos a otra persona.
- **Ranking:** una tabla de líderes muestra a quienes más participan.
- **Retos de comunidad:** eventos extra en los que se apuestan puntos; los resuelve un organizador.
- **Ardy:** asistente dentro de la app que acompaña al usuario.
- **Cuenta:** registro e inicio de sesión, con la sesión guardada en el teléfono.

## Arquitectura

```
 Estudiante / Docente / Admin
            │
            ▼
  App Expo / React Native  (Android · iOS · web)
  Expo Router · NativeWind · cámara para QR
            │  HTTP (JSON)
            ▼
  API Express
  usuarios · saldo · transferencias · eventos · ranking
            │
            ▼
  Libro de movimientos encadenado por hash
  (blockchain simulada, guardada en JSON)
```

**Por qué un libro encadenado:** cada transacción de puntos guarda el hash de la anterior. Si alguien edita un movimiento viejo, la cadena deja de cuadrar. Así nadie puede alterar el historial de la economía sin que se note, y sin necesidad de una blockchain real.

## Herramientas e infraestructura

| Capa | Herramienta |
|------|-------------|
| App | Expo SDK 54, React Native 0.81, React 19, TypeScript |
| Navegación | Expo Router, React Navigation (pestañas y pilas) |
| Estilos | NativeWind (Tailwind para React Native) |
| Cámara y QR | expo-camera, react-native-qrcode-svg |
| Sesión local | AsyncStorage |
| API | Express 5 |
| Persistencia | Archivo JSON con una cadena de bloques simulada |

## Endpoints principales

| Método | Ruta | Para qué |
|--------|------|----------|
| POST | `/register`, `/login` | Cuenta |
| GET | `/balance/:publicId`, `/transactions/:publicId` | Saldo e historial |
| POST | `/transfer` | Transferir puntos |
| GET | `/chain` | Ver el libro de movimientos |
| GET | `/leaderboard` | Ranking |
| GET / POST | `/events`, `/events/:id/claim` | Actividades y reclamo de puntos |
| POST | `/events-extra`, `/events-extra/:id/bet`, `/events-extra/:id/resolve` | Retos de comunidad |

## Cómo correrlo

Desde el repositorio privado:

```bash
npm install
node server/server.js   # API
npm start               # Expo (después: a para Android, i para iOS, w para web)
```

## Estado

Prototipo funcional, terminado en noviembre de 2025. El desarrollo está en pausa y abierto a venta o a que alguien lo continúe. Para llevarlo a producción faltaría cambiar el archivo JSON por una base de datos y definir con la universidad las reglas de la economía de puntos.
