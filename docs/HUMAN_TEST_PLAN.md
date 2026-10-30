# Plan de pruebas humanas

## Fase 0 con el simulador (sin credenciales de Meta)

Preparación: ejecuta `botConfigurable.bat`. Se abre http://localhost:5173; entra con
`admin@demo.local` / `demo-admin-2026`.

| # | Acción | Resultado esperado |
|---|---|---|
| 1 | `scripts\simulate.bat "Hola"` | En pocos segundos aparece la conversación de "Cliente Demo" con el menú del bot, marcado **Enviado** |
| 2 | `scripts\simulate.bat 1` | El bot responde el horario y vuelve a mostrar el menú |
| 3 | `scripts\simulate.bat "quiero algo"` | El bot dice que no entendió y repite el menú |
| 4 | `scripts\simulate.bat Hola --id wamid.prueba --repeat 3` | El mensaje aparece **una sola vez**, con una sola respuesta |
| 5 | `scripts\simulate.bat BAJA` | El bot confirma la baja |
| 6 | Espera 2 s y ejecuta `scripts\simulate.bat 2` | Las respuestas aparecen en rojo: **Bloqueado: el contacto pidió no recibir mensajes** |
| 7 | `scripts\simulate.bat ALTA` | El bot confirma el alta y los mensajes siguientes vuelven a salir |
| 8 | `scripts\simulate.bat Hola --from 5215550002222 --name "Otra persona"` | Aparece una segunda conversación arriba en la lista |
| 9 | Copia el id de una respuesta del bot (en los logs del worker, `fake_message_sent`) y ejecuta `scripts\simulate.bat --status ID read` | Ese mensaje pasa a **Leído** |

La ventana de 24 h se prueba de forma automática en `tests/e2e/test_fase0.py`, porque requiere
mover el reloj.

## Fase 0 con WhatsApp real (cuando haya credenciales)

1. En Meta for Developers, crea la app con WhatsApp y anota del número de prueba:
   `phone_number_id`, token de acceso y app secret.
2. En `.env`:
   - `WHATSAPP_SEND_MODE=real`
   - `WHATSAPP_ACCESS_TOKEN=<token>`
   - `WHATSAPP_APP_SECRET=<app secret>`
   - `WHATSAPP_VERIFY_TOKEN=<un texto tuyo>`
   - `SEED_PHONE_NUMBER_ID=<phone_number_id>`
3. Reinicia con `botConfigurable.bat`. El seed registra ese número para el inquilino `demo`.
4. Abre un túnel: `cloudflared tunnel --url http://localhost:8010`.
5. En Meta, configura el webhook:
   - URL: `https://<tunel>/api/v1/webhook/whatsapp`
   - Verify token: el de `WHATSAPP_VERIFY_TOKEN`
   - Campo: `messages`
6. Desde tu teléfono (agregado como destinatario de prueba), repite los pasos 1 a 7 escribiendo
   al número de prueba. Las respuestas deben llegar al teléfono y los estados de entrega
   (Entregado, Leído) deben verse en el inbox.

## Fases siguientes (pendientes)
1. Consulta de número de parte → imagen + texto (Fase 3).
2. Agendar, reprogramar y cancelar una cita (Fase 4).
3. Lead desde click-to-WhatsApp → calificación → cita → GoHighLevel (Fase 5).
4. Campaña segmentada → baja y bloqueo por límite (Fase 6).
5. Grupos (OBA) → respuesta del bot (Fase 7).
