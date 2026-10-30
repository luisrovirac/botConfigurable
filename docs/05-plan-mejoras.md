<!-- Fecha: 2026-10-30. Origen: revisión completa del código, infraestructura, tests y documentación. -->

# Plan de mejoras de botConfigurable: base estándar + Fase 0 real

## Estado
| Etapa | Estado |
|---|---|
| Etapa 1: base estándar y bugs críticos | **Completa (2026-10-30).** Ver CHANGELOG y ADR 0004 |
| Etapa 2: Fase 0 real | Pendiente |

Cambios respecto a lo planificado en la Etapa 1:
- Los routers de relleno se quitaron ya en esta etapa, no en la 2.7.
- Los permisos de `bot_app` pasaron a la migración 0006.
- El worker y MinIO quedaron en perfiles opcionales de compose.
- Los tests usan la base de compose en lugar de testcontainers.

## Contexto

Revisé el proyecto completo: backend, infraestructura, tests y CI, y la documentación contra el código. El CHANGELOG y `docs/adr/0002-fase0-completada.md` dicen que la Fase 0 está terminada, pero el código no lo respalda:

- **Partes sólidas:**
  - RLS con el rol `bot_app` sin privilegios.
  - Verificación HMAC de la firma.
  - argon2 y helpers de JWT.
  - Migraciones (ya corregidas).
  - Lanzador `botConfigurable.bat`.
- **Stubs que devuelven valores fijos:** LLM, RAG, FSM, packs, catálogo, agenda, CRM, campañas, inbox, adaptador de WhatsApp y worker. El worker escribe un log y termina.
- **El flujo de WhatsApp falla en ejecución en 5 puntos** (verificados):
  1. `webhook.py` importa `SessionLocal` cuando todavía vale `None`, así que siempre responde 500.
  2. `SET LOCAL app.tenant_id = :param` no es SQL válido con parámetros.
  3. El servicio hace commit y se pierde el tenant antes de insertar en el outbox.
  4. Los modelos no coinciden con las migraciones (`contact.name`, `conversation.status`/`assigned_to`, `message.type`, `webhook_event.updated_at`).
  5. La verificación GET de Meta nunca pasa: faltan los alias `hub.mode`, `hub.verify_token` y `hub.challenge`.
- **Otros bugs:**
  - El paquete `calendar` choca con el módulo `calendar` de Python y no se puede importar (verificado).
  - Si falta el secreto, el webhook acepta mensajes sin firma.
  - El reenvío de un mismo webhook duplica mensajes.
  - El lock usa `hash()`, que da un valor distinto en cada proceso.
  - `TenantPackBinding.is_active` es booleano en Python pero `String` en la base.
  - `migrations/env.py` no importa los modelos, así que el autogenerate propondría borrar todo.
  - `bot_app` puede escribir en `pack` y `pack_version`, que son globales.
- **Lo estándar no funciona:**
  - No es repositorio git y no tiene `.gitignore` (el `.env` real está en la raíz).
  - `pip install -e .` falla porque hatchling no sabe qué empaquetar.
  - ruff y mypy strict fallan.
  - Los 8 tests son `assert True` o búsquedas de texto; uno excluye justo el único archivo que viola la regla.
  - El CI fallaría en el paso de instalación.
  - Falta la dependencia `pyyaml`.

**Lo que decidiste:** Etapa 1 deja la base estándar y corrige los bugs. Etapa 2 hace que la Fase 0 cumpla su criterio de aceptación. Las Fases 1 a 8 quedan como hoja de ruta. No hay credenciales de Meta todavía, así que la Fase 0 se valida con un simulador y la prueba real queda como paso final.

**Cómo se ejecuta:** etapa por etapa, cumpliendo `RULES.md`:
- Inyección de dependencias con una composition root.
- Primero los Protocol y después las implementaciones.
- Puntos de entrada delgados.
- Configuración validada al arrancar.
- Sin `except Exception`.
- Reintentos con backoff.
- Cobertura de al menos 80% en los módulos críticos.

---

## Etapa 1: base estándar y bugs críticos

### 1.1 Higiene del repositorio
- Crear `.gitignore` (`.env`, `node_modules`, `__pycache__`, `.pytest_cache`, `.venv`, `backup_pre_bat/`), `.editorconfig` y `.pre-commit-config.yaml` (ruff check, ruff format, mypy).
- Ejecutar `git init` y hacer un primer commit sin `.env`. Borrar `backup_pre_bat/` al terminar la etapa, porque git pasa a ser el respaldo.

### 1.2 Empaquetado e imagen
- En `pyproject.toml`:
  - `[tool.hatch.build.targets.wheel] packages = ["apps/api/src/..."]`, o tratar `apps/api/src` como raíz de fuente.
  - Agregar `pyyaml` y `types-PyYAML`.
  - Mover las dependencias aún sin uso (opentelemetry) a un extra opcional (YAGNI).
  - `httpx`, `tenacity` y `redis` se usan en la Etapa 2.
- Crear un lockfile con `uv lock` para que las builds sean reproducibles.
- `infra/Dockerfile.api` en varias etapas:
  - Imagen `runtime` sin dependencias de desarrollo y con usuario no-root.
  - Imagen `dev` con dependencias de desarrollo y `tests/`.
  - Volver a `pip install .` cuando el empaquetado funcione, sin el truco de `tomllib`.

### 1.3 Lint y tipos
- Configurar `mypy_path = "apps/api/src"` y `explicit_package_bases`. Borrar `apps/api/src/__init__.py`.
- Configurar `[tool.ruff] exclude` y `extend-immutable-calls` para `Depends` y `Header` de FastAPI. Ejecutar `ruff format`.
- Corregir lo que reporten: imports sin usar, `-> dict` sin parámetros, `except` sin `from`, `datetime.utcnow()` y el parámetro `hash`.
- Agregar `pythonpath = ["apps/api/src"]` en la configuración de pytest.

### 1.4 Bugs críticos del backend
| Bug | Corrección |
|---|---|
| `SessionLocal` capturado como `None` | Eliminar el global mutable. Crear el engine y la sessionmaker en un `lifespan` (reemplaza a `on_event`, que está obsoleto) y guardarlos en `app.state`. Las rutas reciben la sesión por `Depends`. El dispose se hace al apagar |
| `SET LOCAL` con parámetro | `SELECT set_config('app.tenant_id', :t, true)` en un solo lugar, `core/tenant.py`. Borrar el `tenant_session` duplicado de `core/db.py` (DRY) |
| Commit dentro de los servicios | Una unidad de trabajo por punto de entrada: la dependencia o el worker abre la transacción, fija el tenant y hace commit o rollback. Los servicios no hacen commit (también `dead_letter.py`) |
| Modelos distintos de las migraciones | Migración `0006`:<br>• Agrega las columnas que faltan, las FK que declara el ORM y los índices `tenant_id`.<br>• Agrega los unique `contact(tenant_id, phone)` y `webhook_event(tenant_id, provider_message_id)`.<br>• Corrige el tipo de `TenantPackBinding.is_active`.<br>• Revoca la escritura de `bot_app` en `pack` y `pack_version` (quedan solo con SELECT, desde `infra/db/10-app-role.sh`). |
| Verificación GET de Meta | `Query(alias="hub.mode")` y similares, comparando con `secrets.compare_digest` |
| Firma opcional | `Settings` valida al arrancar: en un entorno distinto de `development`, la app falla si faltan `WHATSAPP_APP_SECRET` o `WHATSAPP_VERIFY_TOKEN`, o si `SECRET_KEY` es débil. El webhook siempre exige firma cuando hay secreto |
| `calendar` choca con el módulo de Python | Renombrar a `calendar_sync` |
| `get_settings()` relee `.env` en cada llamada | `@lru_cache` |
| Autogenerate de `migrations/env.py` | Importar los módulos de modelos (un `models/__init__` que los registre) |
| JWT | Usar `datetime.now(UTC)` y agregar un claim `type`; `decode` rechaza un refresh token usado como access token |
| `X-Tenant-ID` lo fija el cliente | Se deja de usar. El tenant sale del JWT (Etapa 2) |

### 1.5 Tests reales
- Usar una base de pruebas `botconfigurable_test` en el mismo Postgres de compose. La crea el init script; en CI, un service container.
- `conftest.py`:
  - Aplica las migraciones con el owner y abre las sesiones de la app como `bot_app`, así RLS se aplica de verdad.
  - Envuelve cada test en una transacción con rollback.
  - Incluye un cliente `httpx.AsyncClient` contra la app.
- Tests:
  - **Arquitectura (reales):**
    - Cada tabla con `tenant_id` tiene una política RLS (consultando `pg_policies` de la base, no buscando texto).
    - Ningún módulo fuera de `core` crea sesiones.
    - Los routers no importan modelos ni hacen commit (con `ast`).
    - Los modelos coinciden con la base (alembic `compare_metadata` vacío).
  - **Aislamiento:** el tenant A no ve ni puede escribir datos del tenant B, y sin tenant no se ven filas.
  - **Unitarios:** firma, verificación GET, normalizador y JWT.
- Borrar los tests de `assert True` y el test que excluye `webhook.py`.
- Cobertura mínima con `fail_under` en los módulos críticos (`core`, `messaging`, `auth`).
- Correr tests dentro de Docker: un servicio `tests` en compose (imagen `dev`) y `scripts\test.bat`, porque el Python local es 3.10.

### 1.6 CI (`.github/workflows/ci.yml`)
- **Job backend:**
  - Python 3.12 con service container de Postgres 17, más el init script del rol.
  - Pasos: `uv sync`, ruff check, ruff format --check, mypy, `alembic upgrade head` y pytest con cobertura.
- **Job web:** `npm ci` y `npm run build`.
- **Job docker:** construir `Dockerfile.api`.
- Caché de pip y npm.

### 1.7 Compose e infraestructura de desarrollo
- `depends_on` con `condition: service_healthy`, `restart: unless-stopped` e imágenes con versión fija (`redis:7.4`, versión de minio).
- Healthcheck del worker.
- `api` en desarrollo con `uvicorn --reload` y `WATCHFILES_FORCE_POLLING=true`, para no reiniciar a mano al cambiar código; actualizar el mensaje de `botConfigurable.bat`.
- `/readyz` comprueba la base y Redis.
- `scripts/wait-docker-up.bat` deja de mostrar los puertos viejos. `.env.example` agrega `APP_DB_PASSWORD` y la sección de Meta.
- MinIO y Caddy/cloudflared quedan fuera de esta etapa; se documentan como pendientes para el despliegue.

### 1.8 Frontend base
- Configurar Tailwind de verdad (`tailwind.config`, `postcss`, `index.css`), ESLint, `vite-env.d.ts` y un proxy de Vite `/api` → `http://localhost:8010`.
- Quitar las dependencias sin uso hasta que se necesiten.

### 1.9 Documentación con el estado real
- Corregir el CHANGELOG y reemplazar el ADR-0002 con el ADR `0003-estado-real-fase0.md`.
- README con la guía de desarrollo: `botConfigurable.bat`, puertos, `scripts\test.bat`.
- `DEPLOY.md`: npm en vez de pnpm, seed real, Caddy marcado como pendiente.

**Criterio de cierre de la Etapa 1:** pasan ruff, mypy strict y pytest (con tests reales y cobertura mínima) dentro de Docker y en CI; el webhook procesa un mensaje firmado sin error 500; `botConfigurable.bat` sigue funcionando.

---

## Etapa 2: Fase 0 real (walking skeleton)

Criterio de aceptación de `docs/00-PLAN-MAESTRO.md` §7, validado con el simulador:
- Un mensaje entrante recibe respuesta y aparece en el inbox.
- Reenviar el webhook no duplica nada.
- Con la ventana de 24 h cerrada, la respuesta queda como `blocked_window`.

### 2.1 Resolver el tenant antes de tener contexto
- **Decisión:** funciones SQL `SECURITY DEFINER`, cuyo dueño es el owner y con `EXECUTE` solo para `bot_app`:
  - `resolve_tenant_by_phone_number_id(text)` para el webhook.
  - `find_user_for_login(email)` para el login.
  - `list_active_tenants()` para el worker.
- Así `bot_app` sigue sin BYPASSRLS y la excepción queda acotada y auditable. Se registra en un ADR.
- Tabla `channel_account` (tenant_id, provider, phone_number_id, display_number, credential_ref).

### 2.2 Entrada de mensajes: guardar primero, procesar después
- El webhook valida la firma, resuelve el tenant e inserta el evento crudo en `webhook_event` con `ON CONFLICT DO NOTHING` (esto da la idempotencia). Responde 200 enseguida, como recomienda Meta.
- El worker toma los eventos pendientes con `FOR UPDATE SKIP LOCKED`. Por cada mensaje del lote:
  - Hace upsert de `contact` y `conversation` usando los unique.
  - Inserta `message` de forma idempotente.
  - Actualiza `messaging_window.last_inbound_at`.
  - Guarda los `statuses` en `message_status_event`.
- Tablas nuevas: `channel_account`, `messaging_window` y `message_status_event`, todas con RLS (migración `0007`).

### 2.3 Lock y debounce
- Lock por conversación con `pg_advisory_xact_lock(hashtext(tenant_id || conversation_id))`. Es estable entre procesos y se libera con la transacción.
- Debounce: el evento queda con `process_after = now() + DEBOUNCE_MS` (configurable). El worker agrupa los mensajes seguidos de una misma conversación. Redis no hace falta para esto, así que se quita de compose si nada más lo usa (YAGNI) y la decisión se registra en el ADR.

### 2.4 Flujo mínimo con FSM
- `FlowEngine`: un Protocol en `flows/engine` más una implementación con un registro de nodos (Strategy). El estado se guarda en `flow_instance`, que tendrá modelo ORM.
- Flujo demo de 2 nodos con una herramienta: saludo/menú → `answer`, que responde según la opción (por ejemplo, horario o ubicación). Se define en `packs/demo/flow.yaml` y lo carga un `PackLoader` mínimo real, que valida con pydantic.
- El engine no envía nada. Solo genera mensajes al outbox, con un `idempotency_key` determinístico (`inbound_message_id:node`).

### 2.5 Política de envío (SendPolicy)
- Reglas componibles (Strategy), en orden:
  1. Lista de supresión: `blocked_consent`.
  2. Ventana de 24 h cerrada y sin plantilla: `blocked_window`.
  3. Si pasa todo, `allowed`.
- Palabras de baja (BAJA, STOP, configurables por tenant): escriben en `suppression_list` y en `consent_event`, y responden una confirmación.

### 2.6 Worker y adaptador de WhatsApp
- `apps/worker/main.py` hace de composition root:
  - Bucle con dos consumidores: eventos de entrada y outbox.
  - Apagado ordenado con SIGTERM.
  - Logging configurado.
- `MessagingAdapter`: un Protocol con dos implementaciones, elegidas por `WHATSAPP_SEND_MODE`:
  - `WhatsAppCloudAdapter` usa `httpx` contra la Graph API y reintenta con `tenacity` (backoff exponencial) los errores transitorios.
  - `FakeWhatsAppAdapter` registra el mensaje y devuelve un ID; se usa mientras no haya credenciales.
- Fallos:
  - Un error permanente o pasar el umbral de intentos manda el mensaje a `dead_letter`.
  - Si se envía, el mensaje queda `sent` con su `provider_message_id`.
- Métricas: incrementar los contadores que ya existen en `core/metrics.py`.

### 2.7 Login mínimo e inbox de solo lectura
- `POST /api/v1/auth/login` real: argon2 más `find_user_for_login`. El JWT lleva `tenant_id` y `role`, y `/auth/refresh` rota los tokens.
- `get_current_principal` reemplaza a `X-Tenant-ID`: el tenant sale del token.
- Endpoints `GET /api/v1/conversations` y `GET /api/v1/conversations/{id}/messages`, con esquemas pydantic de respuesta. Los mensajes bloqueados muestran su estado.
- Todas las rutas pasan a `/api/v1`. Los stubs de catálogo, leads y demás se quitan del router hasta su fase, para no exponer endpoints vacíos.
- Frontend: login y una lista de conversaciones con sus mensajes (react-query). La interfaz va en español.

### 2.8 Seed y simulador
- `scripts/seed.py --demo`, idempotente: tenant `demo`, `channel_account` con un `phone_number_id` falso y usuario admin. El .bat lo ejecuta en cada arranque.
- `scripts/simulate_whatsapp.py`: envía webhooks firmados (texto, reenvío, estado y mensaje fuera de la ventana) a `http://localhost:8010`, para probar a mano sin Meta.
- Test E2E (`tests/e2e/test_fase0.py`) con el adaptador falso y `respx`:
  - Entra un mensaje, se responde y aparece en el inbox.
  - Reenviar el webhook no duplica nada.
  - Con la ventana cerrada, la respuesta queda `blocked_window`.
  - La palabra BAJA suprime los envíos siguientes.

### 2.9 Prueba real (cuando tengas credenciales)
- Número de prueba de Meta más un túnel rápido de `cloudflared` hacia `localhost:8010`.
- Poner `WHATSAPP_SEND_MODE=real` en `.env` y ejecutar el plan `docs/HUMAN_TEST_PLAN.md`, actualizado con estos pasos.

---

## Hoja de ruta posterior (resumen; cada fase con su propio plan)
| Fase | Qué falta en lo esencial |
|---|---|
| 1 Inbox y handoff | Inbox completo (asignar, etiquetas, notas, búsqueda), traspaso bot↔humano, RBAC con permisos, escritura de `audit_log`, Instagram |
| 2 Packs, RAG y agente | Packs con borrador → validación → publicación y transcripciones golden, base de conocimiento con pgvector, adaptadores reales de Anthropic y Ollama, grounding, registro de costos |
| 3 Refacciones | Búsqueda en cascada (pg_trgm), importador CSV/XLSX, medir precisión con 50 consultas |
| 4 Clínica | Disponibilidad real, Google Calendar, recordatorios persistentes (`scheduled_task`), reseñas, reportes |
| 5 Seguros | Calificación de leads, GoHighLevel vía outbox, round-robin persistente |
| 6 Campañas | Sincronización de plantillas, segmentos, dispatcher por lotes con tope de marketing |
| 7 Grupos | Grupos de WhatsApp y Telegram |
| 8 Autoservicio | Editor de packs, retención y purga de datos personales |
| Transversal | Filtro de datos personales en logs, cifrado AES-GCM de tokens de terceros, backups, Caddy y cloudflared en compose, OpenTelemetry, compose de producción |

---

## Archivos principales que se tocan
- **Configuración y herramientas:** `pyproject.toml`, `infra/Dockerfile.api`, `infra/docker-compose.yml`, `infra/db/10-app-role.sh`, `.github/workflows/ci.yml`, `.gitignore`, `.pre-commit-config.yaml`.
- **Núcleo:** `apps/api/src/core/{config,db,tenant,security}.py`, `apps/api/src/api/{main,deps}.py`, `apps/api/src/api/v1/{webhook,auth}.py` y el nuevo `conversations.py`.
- **Mensajería:** `apps/api/src/messaging/*` (pipeline, consumidores, send_policy con reglas, lock, adaptadores), `apps/api/src/flows/*`, `apps/api/src/packs/loader.py`, `apps/worker/main.py`.
- **Migraciones:** `0006` (alinear modelos con la base) y `0007` (channel_account, ventana, estados, funciones SECURITY DEFINER), más `migrations/env.py`.
- **Tests y scripts:** `tests/` (conftest, architecture, integration, unit, e2e), `scripts/{seed,simulate_whatsapp}.py`, `scripts/test.bat`, `botConfigurable.bat`.
- **Frontend:** `apps/web` (Tailwind, proxy, login, inbox).
- **Documentación:** este documento, ADRs, README, CHANGELOG, DEPLOY.

**Se reutiliza:** `core/security.verify_signature` (correcto), `auth/password.py` (argon2), `catalog/normalizer.py`, `core/metrics.py`, el SKIP LOCKED de `messaging/worker_consumer.py`, `infra/db/10-app-role.sh` y el lanzador `.bat`.

## Verificación
1. `scripts\test.bat`: ruff, mypy strict y pytest con cobertura dentro de Docker, todo en verde.
2. CI en GitHub en verde (después de `git init` y de subirlo a un remoto, si lo hay).
3. `botConfigurable.bat` levanta todo, ejecuta el seed y las migraciones sin avisos, y `/readyz` responde ready.
4. `python scripts/simulate_whatsapp.py`:
   - La respuesta aparece en el inbox del frontend (login con el usuario del seed).
   - El reenvío no crea filas nuevas.
   - El caso fuera de ventana muestra `blocked_window`.
5. `alembic downgrade base` y luego `upgrade head` funcionan, y `compare_metadata` queda vacío.
6. Cuando haya credenciales: prueba real con el número de prueba de Meta (2.9).
