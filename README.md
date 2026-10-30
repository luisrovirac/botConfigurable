# botConfigurable

Plataforma conversacional configurable, multiinquilino y multicanal (WhatsApp primero).

- **Estado:** Fase 0 funcionando: un mensaje de WhatsApp recibe la respuesta del flujo y se ve en
  el inbox. Validada con el simulador; falta la prueba con WhatsApp real.
  Ver `docs/05-plan-mejoras.md`.
- **Reglas de código:** `RULES.md`. **Decisiones:** `docs/adr/`.

## Desarrollo local (Windows)

Requisitos: Docker Desktop, Node 20+, Git. **No** hace falta Python local: el tooling de Python
corre en Docker (el proyecto usa Python 3.12).

| Tarea | Comando |
|---|---|
| Arrancar todo (Docker, migraciones, seed, API, worker, frontend, navegador) | `botConfigurable.bat` |
| Simular un cliente de WhatsApp | `scripts\simulate.bat "Hola"` (más ejemplos: `docs/HUMAN_TEST_PLAN.md`) |
| Formato, lint, tipos y tests | `scripts\test.bat` (argumentos extra van a pytest: `scripts\test.bat tests/unit -k jwt`) |
| Ver logs de la API y el worker | `scripts\dev-logs.bat` |
| Apagar todo (los datos se conservan) | `scripts\dev-stop.bat` |

Puertos (en `scripts\dev-ports.bat`):

| Servicio | Dirección |
|---|---|
| API | http://localhost:8010 (`/docs`, `/healthz`, `/readyz`, `/metrics`) |
| Frontend | http://localhost:5173 (`/api` se reenvía a la API) |
| Postgres | `localhost:5442`, con las bases `botconfigurable` y `botconfigurable_test` |

Acceso al panel: `admin@demo.local` / `demo-admin-2026` (lo crea el seed).

La API y el worker se recargan solos al guardar cambios en `apps/` (y el worker, también en
`packs/`).

### Cómo funciona un mensaje
1. Meta (o el simulador) llama a `POST /api/v1/webhook/whatsapp`. Se valida la firma, se
   resuelve el inquilino por el número y se guarda en la cola.
2. El worker procesa la cola:
   - guarda el mensaje;
   - corre el flujo (`packs/demo/flow.yaml`);
   - encola las respuestas;
   - las envía según la política (ventana de 24 h y consentimiento).
3. El panel muestra la conversación y el estado de cada respuesta.

Para cambiar lo que responde el bot, edita `packs/demo/flow.yaml`: el worker se reinicia solo.
Sin credenciales de Meta, `WHATSAPP_SEND_MODE=fake` registra los envíos en el log del worker.

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
apps/worker    worker de mensajería (procesa la cola y envía)
apps/web       panel React + Vite + Tailwind
migrations     migraciones Alembic
infra          Docker, compose, script del rol de la base
packs          verticales (refacciones, clínica, seguros)
tests          unit, integration (Postgres real), architecture, e2e
docs           plan maestro, plan de mejoras, ADRs, despliegue
```
