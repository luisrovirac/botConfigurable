# botConfigurable

Plataforma conversacional configurable, multiinquilino y multicanal (WhatsApp primero).

- **Estado:** Etapa 1 (base estándar) completa. La Fase 0 funcional es la Etapa 2.
  Ver `docs/05-plan-mejoras.md`.
- **Reglas de código:** `RULES.md`. **Decisiones:** `docs/adr/`.

## Desarrollo local (Windows)

Requisitos: Docker Desktop, Node 20+, Git. **No** hace falta Python local: el tooling de Python
corre en Docker (el proyecto usa Python 3.12).

| Tarea | Comando |
|---|---|
| Arrancar todo (Docker, migraciones, API, frontend, navegador) | `botConfigurable.bat` |
| Formato, lint, tipos y tests | `scripts\test.bat` (argumentos extra van a pytest: `scripts\test.bat tests/unit -k jwt`) |
| Ver logs de la API | `scripts\dev-logs.bat` |
| Apagar todo (los datos se conservan) | `scripts\dev-stop.bat` |

Puertos (en `scripts\dev-ports.bat`):

| Servicio | Dirección |
|---|---|
| API | http://localhost:8010 (`/docs`, `/healthz`, `/readyz`, `/metrics`) |
| Frontend | http://localhost:5173 (`/api` se reenvía a la API) |
| Postgres | `localhost:5442`, con las bases `botconfigurable` y `botconfigurable_test` |
| Redis | `localhost:6389` |

La API se recarga sola al guardar cambios en `apps/`.

### Base de datos
- La app se conecta como `bot_app`, sin privilegios y sujeta a RLS. Las migraciones usan el
  dueño de las tablas (`DATABASE_OWNER_URL`).
- Para crear una migración:
  ```
  docker compose -f infra/docker-compose.yml --profile tools run --rm tools alembic revision --autogenerate -m "descripcion"
  ```
  Ese comando apunta a la base de tests; revisa el archivo generado antes de aplicarlo.
- Un módulo de modelos nuevo se registra en `apps/api/src/db_models.py`.

### Antes de hacer commit (opcional)
```
pip install pre-commit
pre-commit install
```

## Estructura
```
apps/api/src   API FastAPI (core, auth, messaging, ... por dominio)
apps/worker    worker de mensajería (Etapa 2)
apps/web       panel React + Vite + Tailwind
migrations     migraciones Alembic
infra          Docker, compose, script del rol de la base
packs          verticales (refacciones, clínica, seguros)
tests          unit, integration (Postgres real), architecture
docs           plan maestro, plan de mejoras, ADRs, despliegue
```
