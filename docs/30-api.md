# API

La referencia completa e interactiva está en `/docs` (OpenAPI), por ejemplo
http://localhost:8010/docs en desarrollo.

## Endpoints

| Método | Ruta | Auth | Para qué |
|---|---|---|---|
| GET | `/healthz` | no | El proceso está vivo |
| GET | `/readyz` | no | La base de datos responde (503 si no) |
| GET | `/metrics` | no | Métricas Prometheus |
| GET | `/api/v1/webhook/whatsapp` | token de verificación | Verificación de la suscripción de Meta (`hub.*`) |
| POST | `/api/v1/webhook/whatsapp` | firma `X-Hub-Signature-256` | Mensajes y avisos de entrega de Meta |
| POST | `/api/v1/auth/login` | no | `{email, password}` → `{access_token, refresh_token}` |
| POST | `/api/v1/auth/refresh` | no | `{refresh_token}` → par nuevo |
| GET | `/api/v1/auth/me` | Bearer | Usuario, inquilino y rol del token |
| GET | `/api/v1/conversations` | Bearer | Conversaciones del inquilino, la más reciente primero (`?limit=`, máx. 200) |
| GET | `/api/v1/conversations/{id}/messages` | Bearer | Mensajes en orden; 404 si es de otro inquilino |

## Reglas
- El inquilino sale siempre del token (claim `tenant_id`) o, en el webhook, del
  `phone_number_id` registrado en `channel_account`. Nunca de un dato que mande el cliente.
- `status` de los mensajes salientes:
  - `pending`, `sent`, `delivered`, `read`: estado normal del envío.
  - `failed`: no se pudo enviar.
  - `blocked_window`: la ventana de 24 h estaba cerrada.
  - `blocked_consent`: el contacto pidió no recibir mensajes.
- Errores: 401 si falta el token o es inválido, 403 si la firma o la verificación del webhook
  no coinciden, 400 si el payload es inválido, y 404 si el recurso no existe o es de otro
  inquilino.
