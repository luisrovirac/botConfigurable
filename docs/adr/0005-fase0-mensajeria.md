# ADR 0005: Diseño de la mensajería de la Fase 0

Fecha: 2026-10-30

## Estado
Aceptado

## Contexto
La Etapa 2 (`docs/05-plan-mejoras.md`) implementó el recorrido completo: mensaje de WhatsApp,
cola, flujo, política de envío, envío e inbox. Varias decisiones afectan la seguridad y la
operación, así que conviene dejarlas escritas.

## Decisiones

### Consultas sin inquilino con funciones `SECURITY DEFINER`
Hay tres momentos en que todavía no se conoce el inquilino y RLS no deja ver nada:
- el webhook (¿de qué inquilino es este número?),
- el login (¿de qué inquilino es este email?),
- el worker (¿qué inquilinos tienen trabajo pendiente?).

En vez de darle `BYPASSRLS` a `bot_app`, la migración 0007 crea tres funciones:
`resolve_tenant_by_phone_number_id`, `find_user_for_login` y `tenants_with_pending_work`.
- Corren como el dueño de las tablas y tienen `search_path` fijo.
- Devuelven lo mínimo necesario.
- Solo `bot_app` puede ejecutarlas.
- Se usan únicamente desde `core/tenant_directory.py`.

### El webhook guarda y el worker procesa
- El webhook valida la firma, resuelve el inquilino por `phone_number_id` y guarda cada mensaje
  en `webhook_event`. La idempotencia viene de `ON CONFLICT` sobre
  `(tenant_id, provider_message_id)`.
- Responde 200 enseguida, como pide Meta. Si el número no está registrado, también responde
  200 (y lo registra en el log), porque si no Meta reintentaría para siempre.
- El worker toma los eventos con `FOR UPDATE SKIP LOCKED`, así que se pueden correr varios
  workers sin que se pisen.

### Debounce y lock en Postgres, sin Redis
- **Debounce:** cada mensaje nuevo mueve el `process_after` de los pendientes del mismo
  remitente. Los mensajes seguidos se procesan juntos y se responde al último.
- **Lock:** se toma por conversación con `pg_advisory_xact_lock(hashtext(...))` y se libera
  con la transacción.
- **Redis:** como nada más lo usaba, se quitó de compose, de las dependencias y de `/readyz`
  (YAGNI). Si una fase futura lo necesita (límites de tasa, caché), se vuelve a agregar.

### Ventana de 24 horas calculada desde los mensajes
No hay tabla `messaging_window`. La hora del último mensaje entrante sale de `message`, con el
índice `(conversation_id, created_at)`. Es una sola fuente de verdad y no hay nada que
sincronizar.

### Política de envío como reglas
`RuleBasedPolicy` aplica reglas en orden, y la primera que bloquea decide:
1. `SuppressionRule` (`blocked_consent`).
2. `MessagingWindowRule` (`blocked_window`).

La confirmación de baja está exenta de la supresión. Las plantillas (Fase 6) agregarán una
regla nueva sin tocar las existentes.

### Envío: adaptador real o falso según la configuración
- `WHATSAPP_SEND_MODE=fake` registra el envío sin llamar a Meta. Sirve para desarrollo y tests.
- `WHATSAPP_SEND_MODE=real` usa la Graph API.
- Errores:
  - Temporales (red, 429, 5xx): se reintentan dentro del envío y luego se reprograman con
    backoff.
  - Permanentes, o pasar `OUTBOX_MAX_ATTEMPTS`: el mensaje va a `dead_letter` como `failed`.

### Orden de los mensajes
`message.created_at` usa `clock_timestamp()` y no `now()`. Un entrante y sus respuestas se
guardan en la misma transacción, y así quedan con horas distintas y en orden.

### Autenticación
- El JWT lleva `tenant_id` y `role`. La API toma el inquilino del token y ya no de una cabecera
  que el cliente podía falsificar.
- El refresh emite un par nuevo solo si el usuario sigue activo.
- El login responde igual, y en el mismo tiempo, tanto si el email no existe como si la
  contraseña está mal.

## Consecuencias y pendientes
- **Refresh tokens:** no hay lista de revocación; un refresh token robado sirve hasta que vence
  (7 días). Se resuelve en la Fase 1 (sesiones guardadas o `jti` revocables).
- **Token de Meta:** `WHATSAPP_ACCESS_TOKEN` es uno solo para toda la plataforma. Los tokens por
  cuenta de canal, cifrados, son trabajo transversal (cifrado AES-GCM).
- **Eventos problemáticos:** un evento que falle siempre se reintenta cada 5 segundos (el worker
  registra el error). Falta marcarlo como `failed` tras N intentos; queda para la Fase 1.
