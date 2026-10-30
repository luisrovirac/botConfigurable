# Changelog

## [0.2.0] - Etapa 2: Fase 0 real (2026-10-30)

Criterio de aceptación de la Fase 0 cumplido y probado en `tests/e2e/test_fase0.py`:
- Un mensaje recibe respuesta y aparece en el inbox.
- Reenviar el webhook no duplica nada.
- Fuera de la ventana de 24 h la respuesta queda como `blocked_window`.

Validado con el simulador; falta la prueba con WhatsApp real, a la espera de credenciales.
Decisiones en el ADR 0005.

### Agregado
- **Webhook:**
  - Resuelve el inquilino por el `phone_number_id` de Meta (tabla `channel_account`).
  - Guarda en una cola (`webhook_event`) y responde 200 enseguida.
  - Debounce por remitente.
  - Avisos de entrega en `message_status_event`; el estado del mensaje solo avanza.
- **Worker real:**
  - Bucle con `SKIP LOCKED`, lock por conversación y apagado ordenado.
  - Healthcheck por latido; en desarrollo se reinicia solo al guardar.
- **Flujos:**
  - Motor de máquina de estados con nodos `menu` y `answer` (Strategy).
  - Definición en YAML validada (`packs/demo/flow.yaml`) y estado en `flow_instance`.
- **Política de envío:**
  - Contacto en la lista de supresión: `blocked_consent`. Ventana de 24 h cerrada:
    `blocked_window`.
  - Palabras BAJA/STOP y ALTA/START con registro en `consent_event`.
- **Envío:**
  - Adaptador de WhatsApp Cloud API con reintentos y backoff.
  - Adaptador falso (`WHATSAPP_SEND_MODE=fake`) para desarrollo sin credenciales.
  - Reprogramación con backoff y `dead_letter` tras el máximo de intentos.
- **Login y API:**
  - Login real (argon2id, JWT con `tenant_id` y `role`), refresh y `/auth/me`.
  - Inbox de solo lectura: `GET /api/v1/conversations` y `/{id}/messages`.
- **Base de datos:** migración 0007 con funciones `SECURITY DEFINER` para resolver el inquilino
  sin `BYPASSRLS`.
- **Panel:** login y bandeja de conversaciones con el estado de cada mensaje, en español.
- **Scripts:**
  - `scripts/seed.py --demo`: inquilino, número y admin.
  - `scripts\simulate.bat`: simulador de WhatsApp con firma real.
- **Tests:** 120 en total, con 98,7% de cobertura, incluidos 5 E2E de la Fase 0.

### Cambiado
- Todas las rutas de negocio pasan a `/api/v1`. El webhook ahora es `/api/v1/webhook/whatsapp`.
- El inquilino sale del token o del número de WhatsApp. Se eliminó `WHATSAPP_DEFAULT_TENANT_ID`.
- Se quitó Redis: el debounce y los locks quedaron en Postgres. `/readyz` revisa solo la base.
- El worker arranca por defecto y `botConfigurable.bat` lo levanta después de migrar.

### Corregido
- Logging: `add_logger_name` fallaba con `PrintLogger`; ahora usa loggers de la librería
  estándar.

## [Sin publicar] - Etapa 1: base estándar (2026-10-30)

Plan y estado: `docs/05-plan-mejoras.md`. Decisiones: ADR 0003 y ADR 0004.

### Corregido
- **Webhook de WhatsApp:**
  - Respondía 500 siempre: la sesión ahora se crea en el `lifespan` y se inyecta por dependencia.
  - La verificación GET de Meta nunca pasaba: faltaban los alias `hub.mode`, `hub.verify_token`
    y `hub.challenge`. El token se compara en tiempo constante.
  - La firma ahora es obligatoria siempre. Antes se omitía si faltaba el secreto.
  - El reenvío de un mismo mensaje lo duplicaba. Ahora es idempotente por
    `(tenant_id, provider_message_id)` y procesa todos los mensajes del lote, no solo el primero.
  - Ya no encola una respuesta "Hola" falsa con una conversación inexistente.
- **Inquilino de la transacción:** se fija con `set_config(...)`, porque `SET LOCAL` con
  parámetros no es SQL válido.
- **Commits:** los servicios ya no hacen commit; hay una unidad de trabajo por petición.
- **Modelos y base:** la migración 0006 agrega columnas que faltaban, timestamps NOT NULL,
  índices `tenant_id`, FK y unicidad.
- **Migraciones anteriores:**
  - 0002: RLS de `tenant` sobre `id`.
  - 0004: `"user"` entre comillas.
  - 0005: `downgrade` incompleto.
- **El paquete `calendar` chocaba con el módulo de la librería estándar:** ahora es `calendar_sync`.
- **El lock por conversación** usaba `hash()` de Python, distinto en cada proceso. Ahora usa
  `pg_advisory_xact_lock(hashtext(...))`.
- **La imagen Docker no compilaba.**

### Agregado
- **Base de datos y seguridad:**
  - Rol `bot_app` sin privilegios: la app se conecta con él y RLS se aplica de verdad.
    `DATABASE_OWNER_URL` queda solo para migraciones.
  - Validación de configuración al arrancar: fuera de development/test se exige una
    `SECRET_KEY` fuerte.
  - `TokenService` (JWT con claim `type`) y `PasswordService` (argon2id con rehash).
- **API:**
  - `/readyz` revisa la base y Redis.
  - Logs JSON también para las librerías.
- **Tests reales (61, cobertura del 99% en core/auth/api/messaging):**
  - Unitarios.
  - Integración contra Postgres, incluido el aislamiento entre inquilinos.
  - Arquitectura: RLS por tabla, modelos iguales a la base y reglas de `RULES.md` sobre el AST.
- **Herramientas:**
  - uv con `uv.lock`, ruff (lint y formato), mypy strict, pre-commit y `.editorconfig`.
  - `scripts\test.bat` corre todo en Docker; el CI usa el mismo `scripts/check.sh`.
  - CI con Postgres y Redis, más jobs para el frontend y la imagen de producción.
- **Docker:**
  - Imagen en varias etapas: `runtime` sin dependencias de desarrollo y con usuario no-root;
    `dev` con las herramientas.
  - Compose con healthchecks, `depends_on` por salud, versiones fijas y recarga automática de
    la API.
- **Frontend:**
  - Tailwind configurado de verdad, ESLint y proxy `/api` hacia la API local.
- **Lanzador:**
  - `botConfigurable.bat` para arrancar el entorno local.
  - Puertos compartidos en `scripts\dev-ports.bat`.

### Cambiado
- **Stubs y endpoints:**
  - Los stubs de fases futuras lanzan `NotImplementedError` con la fase en lugar de devolver
    datos inventados.
  - Se quitaron los endpoints que solo devolvían listas vacías (catálogo, leads, citas,
    campañas, packs, inbox).
  - `POST /auth/login` responde 501 hasta la Etapa 2. Antes devolvía tokens falsos.
- **Servicios opcionales:** el worker y MinIO pasan a perfiles opcionales de compose.
- **Dependencias:**
  - Backend: se agregó `pyyaml` y se quitaron las de OpenTelemetry, que nada usaba.
  - Frontend: se quitaron react-query, react-hook-form, zod e i18next, que nada usaba.

## [0.1.0] - 2026-10-27
Estructura inicial. **Nota (2026-10-30):** esta versión listaba como hechas funcionalidades
que en el código eran stubs o no funcionaban. El estado real está en el ADR 0003.
