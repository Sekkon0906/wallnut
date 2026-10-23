# Wallnut (Ardys)

Wallnut es la idea de una aplicación universitaria con una wallet digital gamificada. Estudiantes, docentes y administradores usarían "Ardys", un sistema de puntos para incentivar la participación en eventos y canjear recompensas.

> **Estado:** concepto. Este repositorio todavía no tiene código; solo contiene este README. Lo que sigue describe el alcance previsto, no funcionalidades implementadas.

## Qué es

Una plataforma que pretende reunir en un solo lugar tres cosas:

- **Gestión académica:** eventos, actividades y participación de la comunidad universitaria.
- **Economía digital:** un saldo de puntos Ardys por usuario, con un historial de lo que gana y de lo que gasta.
- **Interacción social:** visibilidad de la participación y de las recompensas.

## Arquitectura

Arquitectura prevista. Todavía no está implementada.

```
 Estudiante / Docente / Admin
            │
            ▼
   Frontend web (Next.js)
            │  HTTP / API routes
            ▼
   Lógica de negocio
   (usuarios, roles, eventos, saldo Ardys)
            │
            ▼
       PostgreSQL
```

## Herramientas e infraestructura

Stack previsto. Todavía no hay dependencias declaradas en el repositorio.

| Capa | Herramienta prevista |
|------|----------------------|
| Frontend | React / Next.js con TypeScript |
| Base de datos | PostgreSQL |

## Funcionalidades previstas

- Tres roles: estudiante, docente y administrador.
- Asignar Ardys por asistir o participar en eventos.
- Consultar el saldo y el historial de movimientos.
- Canjear recompensas.

Ninguna de estas funcionalidades está implementada todavía.

## Cómo correrlo

No aplica: el repositorio aún no contiene código ejecutable.

## Estructura

```
wallnut/
└── README.md
```

## Estado

Fase de idea y definición. Falta crear el proyecto base, el modelo de datos (usuarios, roles, eventos, transacciones de Ardys) y la autenticación.
