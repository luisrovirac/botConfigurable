# Plan maestro — Plataforma conversacional configurable ("botConfigurable")

Documento de arquitectura y plan de implementación. Autoridad de estilo: `RULES.md` (raíz del
repositorio). Las decisiones no obvias que se tomen durante la ejecución se registran en
`docs/adr/`.

---

## 1. Contexto

El repositorio está vacío (solo `RULES.md`, que es la autoridad de estilo: interfaces primero, DI,
configuración externalizada y validada al arranque, tipado estricto, logging estructurado, ≥80 %
de cobertura en módulos críticos, YAGNI).

La idea original describía **tres productos distintos** (asistente de clínica 24/7, bot de catálogo
de refacciones, captador de leads de seguros) con un 70 % de infraestructura común. Construirlos
como tres aplicaciones sería triplicar el coste de mantenimiento.

**La generalización que resuelve esto:** una sola plataforma donde *el vertical es configuración, no
código*. Un **vertical pack** (artefacto versionado: flujos + prompts + esquema de catálogo + mapeo
CRM + plantillas + métricas) se valida y se publica desde el panel. Clínica, refacciones y seguros
se entregan como tres packs sobre el mismo motor; un cuarto vertical (barbería, inmobiliaria,
taller) no requiere escribir código.

**Resultado esperado:** plataforma multiinquilino y multicanal, operable desde un panel en español,
desplegada en el servidor local del usuario tras un túnel de Cloudflare, con los tres verticales
funcionando y documentada para operar y capacitar.

### Decisiones ya tomadas

| Tema | Decisión |
|---|---|
| Alcance | Núcleo configurable **+ los tres verticales** |
| Despliegue | Servidor local propio, Docker Compose, ingreso por `cloudflared` |
| IA | Ports desacoplados; **adaptador Ollama local probado** junto al proveedor en nube |
| Grupos | `GroupChannelAdapter` con **dos implementadores reales**: WhatsApp Groups API oficial (OBA) y Telegram. Difusión 1:1 con plantillas para comunicación masiva. **Sin proveedores no oficiales**; el puerto queda documentado para extensión bajo responsabilidad del cliente |

---

## 2. Hallazgo verificado: la Groups API oficial **sí** existe

El supuesto inicial era que la Cloud API no soportaba grupos. Es incorrecto. Verificado en la
documentación de Meta:

| Hecho | Valor |
|---|---|
| Requisito | **Official Business Account (OBA)** obligatorio |
| No disponible para | números de la app WhatsApp Business, ni números en *Multi-solution Conversations* |
| Participantes por grupo | **8 máximo** |
| Grupos por número | 10 000 |
| Negocios Cloud API por grupo | 1 |
| Ingreso | **solo por enlace de invitación** (no se puede añadir a la fuerza) |
| Precio | **por mensaje**, no por conversación (modelo distinto al 1:1) |
| Plantillas | funcionan, pero **sin métricas de rendimiento**; Meta recomienda plantillas nuevas, dedicadas a grupos |

**Contratos técnicos exactos (ya confirmados, no hay que adivinar):**

- Recepción: webhook estándar `field: "messages"`; el discriminador es la clave **`group_id`**
  dentro del objeto del mensaje. `from` y `contacts[].wa_id` identifican al participante.
  Tipos no soportados llegan como `type: "unsupported"` con error `130501`.
- Envío: `POST /<API_VERSION>/<PHONE_NUMBER_ID>/messages` con
  `{"messaging_product":"whatsapp","recipient_type":"group","to":"<GROUP_ID>","type":"text",...}`.
  `recipient_type` ahora acepta `group` además de `individual`. Pin/unpin usan el mismo endpoint
  con `type:"pin"`.
- Gestión: `.../groups/reference` (crear/borrar, solicitudes de ingreso, obtener/resetear enlace,
  plantilla de invitación, expulsar participantes, info del grupo, grupos activos, ajustes).

**Consecuencia de diseño:** el modelo de conversación soporta grupos **desde la fase 0**
(`conversation.kind ∈ {direct, group}`), porque meterlo después obliga a abrir el núcleo de
enrutamiento, que de otro modo asumiría "un contacto = una conversación". El límite de 8
participantes hace que el caso de uso real sea *equipos pequeños y atención concertada*, no difusión
masiva — eso se documenta para que la expectativa comercial sea correcta.

Fuentes: [Groups API (Meta)](https://developers.facebook.com/documentation/business-messaging/whatsapp/groups) ·
[Group Messaging reference](https://developers.facebook.com/documentation/business-messaging/whatsapp/groups/groups-messaging) ·
[Group Management reference](https://developers.facebook.com/documentation/business-messaging/whatsapp/groups/reference) ·
[Groups pricing](https://developers.facebook.com/documentation/business-messaging/whatsapp/groups/pricing) ·
[OBA](https://developers.facebook.com/documentation/business-messaging/whatsapp/official-business-accounts) ·
[WhatsApp Group API 2026 (Unipile)](https://www.unipile.com/whatsapp-group-api/) ·
[OBA Groups (Ominiflow)](https://ominiflow.com/blog/whatsapp-groups-api) ·
[Omnichat](https://blog.omnichat.ai/whatsapp-groups-api/)

---

## 3. Decisiones de arquitectura

### 3.1 Stack

| Capa | Elección | Por qué (y qué se descartó) |
|---|---|---|
| Backend | **Python 3.12 + FastAPI + SQLAlchemy 2.0 async + Alembic + Pydantic v2** | Pedido y correcto para I/O-bound. `pydantic-settings` da la validación de configuración al arranque que exige RULES.md §II.6 |
| BD | **PostgreSQL 17** + `pgvector`, `pg_trgm`, `unaccent`, `btree_gin` | Una sola BD para relacional, texto y vectores. Descartado Qdrant/Pinecone: añade operación y transacciones distribuidas para un volumen que Postgres absorbe |
| Colas | **Postgres con `SELECT … FOR UPDATE SKIP LOCKED`** | Outbox transaccional sin *dual-write*, **orden garantizado por conversación** (partition key), reintentos auditables, cero infraestructura nueva en un servidor local. Descartados: Celery/arq (el estado de la cola vive fuera de la transacción de negocio y no dan orden por partición), Temporal (correcto para flujos multi-día, operador demasiado grande para la fase 1) |
| Redis | **solo** rate limiting, locks distribuidos, caché, debounce | No es broker. Si Redis cae, no se pierde trabajo |
| Programación | **`scheduled_task` con `run_at` + idempotency key** | Temporizadores durables en BD. Sobreviven despliegues y son auditables, a diferencia de cron + jobs en memoria |
| Objetos | **MinIO** (API S3) | Compatible con S3 si algún día migra a nube |
| Frontend | **React 18 + TypeScript + Vite + Tailwind + shadcn/ui + TanStack Query + react-hook-form + zod + i18next (es por defecto)** | SPA tras el mismo Caddy. Descartado Next.js: no hay necesidad de SSR/SEO en un panel autenticado |
| Calidad | `ruff`, `mypy --strict`, `pytest` + `pytest-asyncio` + `testcontainers` + `respx`, `playwright` para flujos de panel | |
| Observabilidad | `structlog` (JSON), OpenTelemetry, Prometheus `/metrics`, Sentry opcional | |
| Ingreso | **Caddy + cloudflared (named tunnel)** | Hostname estable y TLS válido para los webhooks de Meta sin abrir puertos. **Crítico:** la verificación de firma `X-Hub-Signature-256` necesita el *body crudo*; ningún proxy debe reescribirlo |

### 3.2 Las seis decisiones caras de revertir (se fijan en la fase 0)

1. **Multiinquilino en dos capas.** `tenant_id` en toda tabla + **filtrado explícito en el
   repositorio** como contrato primario (testeable sin infraestructura) + **RLS como red de
   seguridad**. Un único punto de obtención de sesión, `tenant_session(tenant_id)`, que hace
   `SET LOCAL` *dentro* de la transacción.
   *Por qué así:* los workers y los temporizadores no pasan por el middleware HTTP, y con PgBouncer
   en modo transacción un `SET` sin `LOCAL` contamina la petición siguiente.
   Se acompaña de dos pruebas en CI: una de arquitectura (falla si alguien usa el `sessionmaker`
   directo) y una de aislamiento por tabla (tabla nueva sin RLS ⇒ CI roja).

2. **Un solo dueño del turno.** La **FSM siempre manda**; el LLM es un **nodo** (`agent`) dentro de
   ella, con allow-list de herramientas y condiciones de salida. El LLM es una estrategia de
   transición, no un orquestador paralelo.
   *Por qué así:* dos runtimes compitiendo por el turno produce bugs irreproducibles ("¿el agente
   puede saltarse el opt-in?"). Esto también es OCP real: añadir comportamiento = añadir un tipo de
   nodo.

3. **`SendPolicy` obligatorio en el outbox.** Ningún *call site* decide si puede enviar. La política
   evalúa ventana de 24 h, categoría de plantilla (`marketing` / `utility` / `authentication`),
   límite de plantillas de marketing por usuario, consentimiento, *quiet hours* y zona horaria.
   Si no se puede enviar, el mensaje queda `blocked_window` / `blocked_consent` y **visible en la
   bandeja** — nunca se descarta en silencio.
   *Por qué así:* es la causa número uno de fallos en producción de este tipo de producto, y el
   límite de marketing por usuario silencia campañas sin devolver error: si no se modela, las
   métricas mienten.

4. **Idempotencia en los dos sentidos.** Entrada: `unique(channel_account_id, provider_message_id)`
   sobre `webhook_event`. Salida: `outbox_message.idempotency_key` + orden por `conversation_id`.
   *Por qué así:* `provider_message_id` solo evita procesar dos veces lo que entra; sin clave de
   salida se duplican envíos y efectos (dos citas para el mismo paciente).

5. **Debounce + lock por conversación.** Agregación de ~2,5 s de los mensajes entrantes del mismo
   contacto y concurrencia 1 por `conversation_id`.
   *Por qué así:* si el usuario manda cinco mensajes seguidos, sin esto el bot responde cinco veces
   y con las respuestas intercaladas.

6. **Estado de flujo persistido en BD** (`flow_instance`), no en Redis: debe sobrevivir a los
   despliegues, y cada conversación guarda la `pack_version` que la atendió.

### 3.3 Vertical packs: el mecanismo de generalización

Un pack es un **artefacto inmutable y versionado**, no un registro editable en caliente.

```
pack/
  manifest.yaml        # id, versión semántica, idioma, checksum
  prompts/*.md         # system prompt, tono, guardrails, versionados
  flows/*.yaml         # máquinas de estado
  tools.yaml           # allow-list de herramientas por nodo agente
  catalog.schema.yaml  # atributos tipados del catálogo de este vertical
  crm.mapping.yaml     # campos → GoHighLevel u otro CRM
  templates.yaml       # plantillas de Meta esperadas + variables tipadas
  kb/                  # documentos base de conocimiento
  metrics.yaml         # KPIs del panel para este vertical
  tests/*.transcript.yaml  # conversaciones "golden"
```

- Ciclo de vida: **draft → validate → publish**. Validación = JSON Schema + modelos Pydantic +
  **ejecución de las transcripciones golden**. Un pack no se publica si una transcripción falla.
- Editar = nueva versión. *Rollback* = cambiar el binding `tenant → pack_version`.
- **Fase 1–7: los packs viven como YAML en git.** El editor visual en el panel es la fase 8,
  a propósito: hay que aprender la forma real del pack antes de construir su editor, y un DSL
  editable por no-programadores sin CI es "código sin pruebas".

### 3.4 Puertos (interfaces) y sus implementadores

| Puerto | Implementadores en la entrega | Nota |
|---|---|---|
| `ChannelAdapter` | `whatsapp_cloud`, `instagram`, `sandbox` (tests/demo) | `capabilities()` declara qué soporta cada canal (plantillas, botones, ventana, medios). Instagram **se implementa temprano**: sus reglas difieren (sin plantillas, *human agent tag* de 7 días) y es lo que valida la abstracción antes de que se fosilice |
| `GroupChannelAdapter` | `whatsapp_groups` (OBA), `telegram` | Dos implementadores reales ⇒ abstracción justificada |
| `LLMProvider` / `EmbeddingProvider` | `anthropic`, `ollama` (local), `openai` (opcional) | Default: `claude-sonnet-5-5` para el turno, `claude-haiku-5-5` para clasificar/extraer; Ollama local probado para operar sin coste por token |
| `CalendarAdapter` | `google`, `microsoft_graph` | Se **extrae** en la fase 4, cuando hay dos consumidores reales |
| `CRMAdapter` | `gohighlevel` | Vía outbox; `noop` para tenants sin CRM |
| `ReviewAdapter` | `google_business_profile` | Solo genera y envía el enlace de reseña; publicar reseñas no es posible por API |
| `OutboundWebhook` | genérico (n8n) | Bus de eventos saliente |

**Voz: no se crea puerto ahora.** Se documenta la costura real (la FSM y las herramientas ya son
agnósticas del canal; voz = nuevo `ChannelAdapter` + ASR/TTS + *barge-in*). Una interfaz sin segundo
implementador es abstracción especulativa y viola YAGNI (RULES.md §I.3).

**n8n: integración de borde, no orquestador del turno.** Sin multiinquilino ni versionado por
tenant, y sería un punto único de fallo en la ruta crítica con latencia añadida. Se usa detrás de
`CRMAdapter` / `OutboundWebhook`, y se entregan flujos de ejemplo exportados.

### 3.5 Anti-alucinación (requisito duro, no cosmético)

Un SKU o un precio inventado = pedido equivocado = devolución y cliente perdido. Dos mecanismos:

1. El nodo `agent` **nunca** emite identificadores, precios ni disponibilidad en texto libre:
   **selecciona una plantilla de salida** sobre el resultado estructurado de la herramienta.
2. **Grounding gate** antes de encolar: todo identificador, precio y fecha citados deben existir en
   el resultado de la herramienta de esa misma vuelta. Si no, el mensaje no sale y se registra
   (`grounding_violation`) → reintento acotado o escalada a humano.

Además: umbral de confianza configurable, y *fallback* explícito a humano o a pregunta de
aclaración, con todo registrado en `llm_call` / `tool_invocation`.

---

## 4. Modelo de datos

Agrupado por módulo. Toda tabla lleva `tenant_id`, `created_at`, `updated_at` y RLS.

**Inquilinos / acceso:** `tenant`, `user`, `tenant_membership`, `role`, `permission`,
`role_permission`, `api_key`, `audit_log`, `oauth_credential` (Google/Microsoft/GHL por tenant,
*refresh token* cifrado — bloqueante para las fases 4–5).

**Canales:** `channel_account` (WABA id, `phone_number_id`, tier, OBA sí/no, cuotas),
`rate_limit_bucket`, `message_template` (sincronizada de la Graph API: estado de aprobación,
categoría, variables tipadas, `is_group_template`), `webhook_event` (crudo + idempotencia).

**Contactos y conversación:** `contact`, **`contact_identity`** (`wa_id` / `ig_scoped_id` /
teléfono / email — sin esto no hay bandeja unificada ni CRM), `conversation`
(`kind ∈ {direct, group}`), `group_chat` (`provider_group_id`, enlace de invitación, participantes),
`message`, `message_status_event`, `messaging_window`, `conversation_assignment`
(bot/humano/cola + SLA), `conversation_tag`, `internal_note`.

**Consentimiento:** **`consent_event` append-only** (canal, fuente, texto exacto mostrado,
timestamp, IP/origen) + `suppression_list`. Es evidencia legal; un booleano no sirve.

**Entrega:** `outbox_message` (idempotency_key, intentos, `blocked_reason`, partition key),
`processing_attempt`, `dead_letter`, `scheduled_task`, `media_asset` (hash, `provider_media_id`,
ruta S3 — **las URLs de medios de Meta expiran en minutos, hay que reingestar**).

**Packs y flujos:** `pack`, `pack_version`, `tenant_pack_binding`, `flow`, `flow_version`,
**`flow_instance`** (nodo actual + variables), `prompt_version`.

**IA / conocimiento:** `kb_document` → `kb_chunk` (con `embedding_model` y `dim` guardados por
chunk: cambiar de modelo obliga a re-embeber y hay que saberlo), `retrieval_log`, `llm_call`
(tokens, coste, `prompt_version`, latencia), `tool_invocation`, `feedback_event`.

**Catálogo (genérico, sirve a refacciones, servicios y planes):** `catalog`, `catalog_item`
(atributos tipados en JSONB validados contra `catalog.schema.yaml`), **`item_identifier`**
(`kind ∈ {sku, oem, npc, alias_proveedor, upc}`, `value_normalized`), **`item_fitment`**
(marca/modelo/`year_from`/`year_to`/motor — **modelado, no texto libre**), `item_media`,
`catalog_query_log`, `import_job`.

**Agenda:** `service`, `resource` (profesional/sala/equipo), `availability_rule` (RRULE),
`time_off`, `appointment`, `appointment_status_event`, `external_calendar_link`
(**`external_event_id` + `sync_token`/`etag`: es lo único que evita doble reserva**),
`reminder_schedule`.

**Leads:** `lead`, `lead_source` (QR / click-to-WhatsApp / enlace, con UTM), `lead_score_event`,
`pipeline_stage`, `crm_sync_state`, **`agent_assignment_cursor`** (el round-robin necesita estado
persistido, con *skip* por horario y capacidad).

**Campañas:** `audience_segment` (versionado), `campaign`, `campaign_recipient` (estado por
destinatario), `campaign_metric_rollup`.

> **Campañas nunca encolan 50 000 jobs.** `campaign_recipient` + un *dispatcher* por lotes que
> respeta rate limit por WABA, límite de marketing por usuario, *quiet hours* y zona horaria del
> destinatario.

---

## 5. Búsqueda de catálogo: cascada determinista

Un número de parte es un **identificador**, no lenguaje natural. Full-text genérico es la respuesta
equivocada. Orden de resolución, con corte temprano:

1. **Normalizar** la consulta (mayúsculas, sin guiones/espacios/puntos, `unaccent`).
2. **Exacto** con índice btree sobre `item_identifier.value_normalized`.
3. **Cross-reference** OEM ↔ aftermarket ↔ alias de proveedor (mismo paso 2 sobre otros `kind`).
   *Es el mayor valor del módulo y lo que siempre se omite.*
4. **Prefijo** (`value_normalized LIKE 'ABC%'`).
5. **Trigram** con umbral de similitud, solo sobre el conjunto de candidatos.
6. **Semántica (pgvector)** solo para *descripción* y *aplicación*, nunca para identificadores.
7. **Fitment**: filtro estructurado por marca/modelo/año sobre el resultado.

Respuesta enriquecida: imagen (`item_media`) + caption con SKU, descripción técnica, marca y
aplicación en negrita, generado por **plantilla de salida**, no por el LLM (ver §3.5).
Métrica de aceptación: **precision@1 medida sobre 50 consultas reales**.

Nota de rendimiento: `pgvector` y `pg_trgm` compiten con la ruta caliente de webhooks. **Pool de
conexiones separado y timeouts por tipo de consulta desde el día 1**; réplica de lectura cuando
duela.

---

## 6. Estructura del repositorio

```
botConfigurable/
├─ RULES.md
├─ docs/
│  ├─ 00-PLAN-MAESTRO.md         # este documento
│  ├─ 10-arquitectura.md
│  ├─ 20-modelo-datos.md
│  ├─ 30-api.md                  # además de /docs OpenAPI
│  ├─ 40-packs.md                # cómo crear un vertical sin escribir código
│  ├─ 50-operacion.md            # runbook: despliegue, backups, incidentes
│  ├─ 60-manual-usuario.md       # panel, en español
│  ├─ 70-cumplimiento.md         # opt-in, plantillas, políticas Meta, PII
│  ├─ 80-limitaciones.md         # grupos, voz, reseñas, lo no viable
│  ├─ 90-capacitacion.md         # guion de formación del equipo
│  └─ adr/NNN-*.md
├─ apps/
│  ├─ api/src/
│  │  ├─ core/        # config, db (tenant_session), logging, errors, security, di
│  │  ├─ messaging/   # ports/, adapters/, send_policy, inbound_pipeline, outbox
│  │  ├─ flows/       # engine, nodes/, instance_store
│  │  ├─ ai/          # ports/, adapters/, rag/, grounding, prompts
│  │  ├─ catalog/     # search cascade, importer
│  │  ├─ scheduling/  # availability, appointments, calendar adapters, reminders
│  │  ├─ leads/       # scoring, round_robin, crm adapters
│  │  ├─ campaigns/   # segments, dispatcher
│  │  ├─ inbox/       # asignación, handoff, notas
│  │  ├─ packs/       # loader, validator, registry
│  │  ├─ reporting/
│  │  └─ api/v1/      # routers delgados (RULES.md §II.3)
│  ├─ worker/         # mismo paquete, entrypoint distinto: queue consumer + scheduler
│  └─ web/            # React + Vite
├─ packs/{clinica,refacciones,seguros}/
├─ migrations/        # Alembic
├─ seeds/
├─ infra/             # docker-compose.yml, Caddyfile, cloudflared, Dockerfiles
├─ scripts/
├─ n8n/               # flujos exportados de ejemplo
├─ tests/{unit,integration,e2e,transcripts}/
├─ .env.example
└─ .github/workflows/ci.yml
```

---

## 7. Fases de implementación

Regla transversal para cada fase: **interfaz primero**, migración Alembic propia, pruebas en verde,
`mypy --strict` y `ruff` limpios, documentación y ADR actualizados. Una fase no se cierra sin su
criterio de aceptación verificado.

### Fase 0 — Esqueleto vertical (el *walking skeleton*)

El camino end-to-end más delgado posible, que ya fija las seis decisiones caras de §3.2:

webhook WhatsApp (firma verificada sobre body crudo) → `webhook_event` → cola Postgres → `contact` +
`conversation` + `message` → FSM de dos nodos con una sola herramienta → `outbox_message` con
`SendPolicy` → envío real → `message_status_event` → pantalla de bandeja de solo lectura.

Incluye: `tenant_session` + RLS + los dos tests de aislamiento, debounce, lock por conversación,
`dead_letter`, `/healthz`, `/readyz`, `/metrics`, docker-compose levantando todo, cloudflared.

*Criterio:* un mensaje real de WhatsApp aparece en el panel y recibe respuesta; reenviar el mismo
webhook no duplica nada; con la ventana cerrada y sin plantilla el mensaje queda `blocked_window`
visible en la bandeja.

### Fase 1 — Bandeja, handoff y panel base

Autenticación (JWT + refresh con rotación, argon2id), RBAC, gestión de usuarios y equipos, bandeja
completa (asignación, etiquetas, notas internas, búsqueda), **handoff bot ↔ humano**, historial y
`audit_log`. Al final: **adaptador de Instagram** (valida `capabilities()` y `SendPolicy` con reglas
distintas: sin plantillas, *human agent tag* de 7 días).

*Criterio:* un agente humano atiende WhatsApp **e** Instagram desde el panel y puede tomar y
devolver el control al bot. **La plataforma ya es vendible solo con esto.**

### Fase 2 — Motor de packs, RAG y nodo agente

`pack` loader/validator/registry con draft→validate→publish y transcripciones golden. Base de
conocimiento (ingesta, *chunking*, embeddings con `EmbeddingProvider`), RAG híbrido, nodo `agent`
con tool-calling y allow-list, **grounding gate**, umbral de confianza y fallback, auditoría de
coste/tokens. Adaptadores `anthropic` + `ollama`, con prueba de paridad entre ambos.

*Criterio:* FAQ respondidas con cita a la fuente; sin confianza suficiente se escala a humano; el
coste por conversación es consultable; cambiar de proveedor de IA es una variable de entorno.

### Fase 3 — Vertical 1: refacciones (catálogo)

Catálogo genérico con esquema por pack, `item_identifier`, `item_fitment`, medios, **cascada de
búsqueda de §5**, respuesta imagen + caption, CRUD administrativo, **carga masiva** CSV/XLSX con
validación y reporte de errores, historial de consultas.
*Se elige primero entre los verticales:* no depende de OAuth externo y el "wow" es inmediato.

*Criterio:* busca por NPC/número de parte, descripción y aplicación vehicular; responde con imagen y
caption en negrita con SKU, descripción, marca y aplicación; **precision@1 medida sobre 50 consultas
reales**; ningún SKU inventado (grounding gate en verde).

### Fase 4 — Vertical 2: clínica / servicios 24-7

Núcleo de agenda propio (servicios, recursos, reglas de disponibilidad, zonas horarias, UTC en BD),
agendar/modificar/cancelar/confirmar por conversación, **`CalendarAdapter` extraído aquí** con
Google y Microsoft Graph (`external_event_id` + `sync_token`), recordatorios y confirmaciones con
temporizadores durables, gestión de ausencias, reactivación de inactivos, **solicitud de reseñas**
(`ReviewAdapter` con Google Business Profile, tras cita completada y con opt-in), informes
periódicos configurables, vista de agenda en el panel.

*Criterio:* el ciclo completo de cita funciona por WhatsApp y queda sincronizado en el calendario
externo sin doble reserva; los recordatorios sobreviven a un reinicio; el reporte mensual se genera
y exporta. Con dos consumidores reales del esquema de pack, aquí se **consolida** su contrato.

### Fase 5 — Vertical 3: seguros / leads

Captura por enlace/QR y click-to-WhatsApp con atribución UTM, flujo 100 % en español, bot de
calificación de 3–5 preguntas con scoring configurable, agendado de cita, **GoHighLevel** (crear/
actualizar contacto, etiquetas, pipeline, disparar automatizaciones) vía outbox, **round-robin
persistido** con hasta 20 agentes y *skip* por horario/capacidad, panel de embudo (leads por fuente,
tasa de respuesta, citas agendadas, estado del pipeline).

*Criterio:* un lead entra por anuncio, es calificado, agenda cita, aparece en GoHighLevel con
etiquetas y etapa correctas y queda asignado a un agente; el reparto es equitativo y auditable.

### Fase 6 — Campañas, plantillas y reportes

Sincronización de plantillas con la Graph API, segmentos versionados, campañas programadas con
dispatcher por lotes (rate limit, límite de marketing por usuario, quiet hours, tz), opt-in/opt-out
y supresión, métricas de entrega/lectura/respuesta/conversión/citas, exportación de datos.

*Deliberadamente tarde:* es el módulo donde un bug cuesta el **bloqueo del WABA**, y conviene
construirlo cuando el `SendPolicy` ya está endurecido por cinco fases de uso.

*Criterio:* una campaña a una lista segmentada respeta opt-in y plantillas aprobadas, se detiene
sola al tocar el límite de marketing y reporta por destinatario el motivo de no entrega.

### Fase 7 — Grupos

`GroupChannelAdapter` con **`whatsapp_groups`** (OBA; crear/borrar grupo, enlace de invitación,
plantilla de invitación, expulsar participantes, `recipient_type:"group"`, webhook por `group_id`,
precio por mensaje) y **`telegram`** (webhook, grupos de comunidad). Reglas por grupo: grupos
permitidos, palabras clave, horarios, límites de frecuencia, modo "solo si me mencionan". Contexto
de grupo para el nodo agente. Historial y auditoría de respuestas del bot en grupos.

*Criterio:* el bot responde pertinentemente en un grupo de WhatsApp (OBA) y en un grupo de Telegram,
respetando reglas y límites; `docs/80-limitaciones.md` explica el tope de 8 participantes, el
requisito OBA, la ausencia de métricas de plantillas en grupos y la alternativa de difusión 1:1.

### Fase 8 — Autoservicio y cierre

Editor de packs en el panel (formularios + validación + diff + publish/rollback), importación/
exportación de packs, flujos n8n de ejemplo, reportes personalizables, repaso de seguridad,
retención y borrado de PII, documentación final y material de capacitación.

*Criterio:* una persona no programadora crea un cuarto vertical desde el panel, lo valida y lo
publica, sin tocar código.

---

## 8. Seguridad, cumplimiento y operación

- **Secretos:** `.env` + Docker secrets; tokens de terceros cifrados en BD (AES-GCM con clave
  maestra fuera de la BD). Nunca en logs: *scrubber* de PII en el logger.
- **Cumplimiento Meta:** opt-in registrado como evento con el texto exacto, opt-out por palabra
  clave en cualquier momento, plantillas con categoría correcta, ventana de 24 h respetada por el
  `SendPolicy`, política de privacidad y `docs/70-cumplimiento.md`.
- **PII:** minimización, retención configurable por tenant, job de purga, exportación y borrado a
  petición del titular, `audit_log` de todo acceso a conversaciones.
- **Resiliencia:** reintentos con backoff exponencial y jitter, circuit breaker por integración,
  `dead_letter` con reproceso desde el panel, degradación elegante (si el LLM falla → respuesta de
  cortesía + escalada a humano).
- **Operación:** backup diario de Postgres (`pg_dump` + WAL) y de MinIO, restauración probada y
  documentada, migraciones hacia delante, *runbook* de incidentes en `docs/50-operacion.md`.
- **Despliegue local:** `docker compose up`, Caddy, `cloudflared` como *named tunnel* (hostname
  estable; si cambia, los webhooks de Meta se rompen), healthchecks y política de reinicio.

## 9. Estrategia de pruebas

| Tipo | Qué cubre |
|---|---|
| Unitarias | `SendPolicy`, cascada de búsqueda, scoring, round-robin, disponibilidad y zonas horarias, normalizadores, grounding gate |
| Arquitectura | nadie usa el `sessionmaker` directo; toda tabla tiene RLS; los routers no contienen lógica de negocio |
| Integración | `testcontainers` (Postgres + Redis), `respx` para Graph API / Google / GHL, webhook→respuesta completo, idempotencia, orden por conversación |
| **Transcripciones golden** | conversaciones fixture por pack; **bloquean la publicación** de una versión de pack |
| E2E | Playwright: login, bandeja, handoff, alta de producto, agendar cita, lanzar campaña |
| Carga | ráfaga de webhooks (verifica debounce, locks y que el RAG no ahogue la ruta caliente) |

Objetivo de cobertura: ≥80 % en `messaging`, `flows`, `catalog`, `scheduling`, `leads` (RULES.md §II.14).

## 10. Supuestos, límites y lo que no se construye

**Supuestos** (a confirmar durante la ejecución): se dispondrá de WABA verificado y, para grupos, de
**OBA** (que requiere aprobación de Meta y no es inmediata); las plantillas requieren aprobación
previa; GoHighLevel con plan que exponga API; Google Business Profile aprobado para gestionar la
ficha.

**Limitaciones reales que se documentan en vez de prometerse:** grupos de WhatsApp limitados a 8
participantes y a ingreso por invitación, sin métricas de plantillas; no se pueden *publicar*
reseñas por API, solo solicitar con enlace; Instagram no admite plantillas ni ventana de 24 h
equivalente; la IA puede equivocarse y por eso existen grounding gate y escalada.

**No se construye (decisión explícita):** automatización no oficial de WhatsApp Web (viola los
términos, expone a baneo permanente); puerto de voz sin segundo implementador; n8n en la ruta
crítica del turno; editor visual de flujos antes de la fase 8; base vectorial dedicada.

## 11. Cómo debe ejecutar esto un asistente de IA

1. Leer `RULES.md` completo antes de escribir código (es obligatorio por su §III.10).
2. Trabajar **una fase a la vez**, en una rama por fase; no empezar la siguiente sin el criterio de
   aceptación verificado.
3. Por cada módulo: definir el `Protocol`/ABC → implementar → inyectar por constructor → probar.
   Nunca instanciar dependencias dentro de un método que no sea una fábrica.
4. Ninguna constante de configuración en el código: todo a `Settings` (pydantic-settings) con
   validación al arranque y entrada en `.env.example`.
5. Cada decisión no obvia se registra como ADR en `docs/adr/`.
6. Al terminar cada fase: actualizar `docs/`, el `.env.example`, los seeds y el CHANGELOG.

## 12. Verificación end-to-end de la entrega

```bash
cp .env.example .env            # completar credenciales
docker compose -f infra/docker-compose.yml up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.seed --demo   # tenant demo + 3 packs
docker compose exec api pytest -q --cov                 # unit + integración
cd apps/web && pnpm test:e2e                            # Playwright
```

Luego, con el túnel activo y el webhook registrado en Meta, recorrer los cuatro guiones de
`docs/HUMAN_TEST_PLAN.md`: (1) consulta de número de parte → imagen + caption; (2) agendar,
reprogramar y cancelar cita → verificar en Google Calendar y recibir recordatorio; (3) lead desde
enlace click-to-WhatsApp → calificación → cita → contacto en GoHighLevel con etiqueta y agente
asignado; (4) campaña a lista segmentada → comprobar opt-out y bloqueo por límite de marketing.
Para grupos (requiere OBA): crear grupo, enviar invitación, mensaje en grupo → respuesta del bot.
