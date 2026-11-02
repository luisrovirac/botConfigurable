# Plan para culminar Meta (WhatsApp) — 02-11-2026

Objetivo: que el bot funcione en producción (número real, app publicada, clientes reales).
Base: `docs/pasosQueFaltanAl30-10-2026.md`.

Forma de trabajo: Claude no se conecta al servidor. Pasa los comandos (uno por línea, con
comentarios `#`), Luis los ejecuta y devuelve la salida.

## Estado confirmado (02-11-2026)

### Servidor
| Qué | Estado |
|---|---|
| Contenedores api, db, web, worker | Arriba y healthy |
| `/readyz` local y por internet | `{"status":"ready","database":"ok"}` |
| Verificación del webhook por Meta | OK (dos verificaciones con 200) |
| Mensajes reales recibidos | **Ninguno**: no hay mensajes en la base |
| Único aviso recibido | El botón "Probar" de Meta (número de ejemplo `123456123`) da `webhook_unknown_channel`. Es normal |
| Número registrado en el bot | `1399286213261545` |
| `WHATSAPP_SEND_MODE` | `fake` (simulado) |
| `WHATSAPP_ACCESS_TOKEN` | Vacío |
| `META_API_VERSION` | `v26.0`, ya actual |
| `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN` | Cargados (32 caracteres) |

Nota menor: el token de verificación aparece en los logs de acceso. El riesgo es bajo porque solo
sirve para verificar el webhook. Cambiarlo es opcional.

### Meta (app "Nexosax")
| Qué | Estado |
|---|---|
| App | **Sin publicar** |
| Webhooks, campo `messages` | Configurado y probado ✔ |
| Número de Luis en la lista "Para" | ✔ |
| Identificador del número de prueba | `1399286213261545`, coincide con el bot ✔ |
| Paso 2 de Meta: registrar número, pago, enviar mensaje | Pendiente (para el número real) |
| Paso 3 de Meta: verificación del negocio | Pendiente |

Dónde está cada cosa en Meta (panel nuevo por casos de uso): **Casos de uso → Personalizar →
Conectar en WhatsApp → Configuración básica**:
- **Paso 1. Pruébalo:** "De" y "Para", y el botón *Generar token de acceso*.
- **Paso 2: Configuración de producción:** webhooks, registrar el número y la información de pago.
- **Paso 3: Verificación del negocio.**

## Avance (02-11-2026, tarde)
- Pasos A y B: hechos (el bot responde con el número de prueba).
- Paso C: código listo (commit `f3282f8`), falta desplegarlo.
- Orden nuevo: C → publicar la app (primer punto del Paso E) → D → resto del E. Para que la app
  aparezca al asignar activos al usuario del sistema, conviene publicarla antes.
- URLs para Meta: privacidad `https://botwhatsapp.devsax.site/privacidad`, eliminación de datos
  `https://botwhatsapp.devsax.site/privacidad#eliminar-datos`.

## Pasos que faltan

### Paso A — Token temporal y envío real (pasos 2 y 3 del documento del 30-10)
1. En Meta, **Paso 1. Pruébalo → Generar token de acceso**. Copia el token (empieza con `EAA`).
2. En el servidor:
```bash
# Ir al proyecto
cd ~/projects/botConfigurable

# Editar la configuracion: poner WHATSAPP_SEND_MODE=real y WHATSAPP_ACCESS_TOKEN=EAA...
nano .env.production

# Aplicar el cambio (termina mostrando "ready")
sh scripts/deploy.sh
```

### Paso B — Prueba con el teléfono (pasos 1 y 4 del documento del 30-10)
1. Escribe "Hola" al número de prueba. Debe llegarte el menú del bot.
2. Revisa:
```bash
# Alias para docker compose
alias botc='docker compose --env-file .env.production -f infra/docker-compose.prod.yml'

# Logs de los ultimos 10 minutos: mensaje recibido, envio y errores
botc logs --since 10m --no-log-prefix api worker 2>&1 | grep -iE "webhook|signature|unknown_channel|outbox|error" | tail -20

# Mensajes guardados, por direccion y estado
botc exec -T db psql -U botowner -d botconfigurable -c "select direction, status, count(*), max(created_at) from message group by 1,2 order by 1,2;"
```
3. Cómo leer el resultado:
   - **No aparece nada en los logs:** Meta no envía los mensajes reales mientras la app está sin
     publicar. Se adelanta el Paso C (página de privacidad) y se publica la app.
   - **Aparece `Invalid signature`:** la clave secreta de la app no coincide. Cópiala de nuevo
     desde Configuración de la app → Básica.
   - **Aparece un error 401 o el código 190:** el token es inválido o venció. Genera otro.
   - **Aparece el código 131030:** el número no está en la lista "Para".
4. Si llega el menú, completa la tabla de 6 mensajes del Paso 4 del documento del 30-10.

### Paso C — Página de política de privacidad (código, lo hace Claude)
Meta la exige para publicar la app.
- Una página estática en `https://botwhatsapp.devsax.site/privacidad`: el archivo va en
  `infra/web/` y lo sirve Caddy.
- Incluye las instrucciones para eliminar datos.
- Se despliega con `scripts\package.bat`, copiando el paquete y ejecutando `sh scripts/deploy.sh`.

### Paso D — Token permanente (paso 5 del documento del 30-10)
En business.facebook.com → Configuración del negocio → Usuarios del sistema:
1. Crea un usuario del sistema con rol Administrador.
2. Asígnale la app y la cuenta de WhatsApp, con control total.
3. Genera el token con caducidad "Nunca" y los permisos `whatsapp_business_messaging` y
   `whatsapp_business_management`.
4. Reemplaza el token en `.env.production` y ejecuta `deploy.sh`.

### Paso E — Producción (Pasos 2 y 3 de Meta)
1. Publicar la app con la URL de privacidad.
2. Agregar el número real del negocio. No puede estar usando la app normal de WhatsApp.
   Verificarlo con SMS o llamada.
3. Registrar el número en la Cloud API: `POST /{phone_number_id}/register` con PIN. Claude pasa el `curl`.
4. Suscribir la app a la cuenta de WhatsApp Business real: `POST /{waba_id}/subscribed_apps`.
   Sin esto no llegan los mensajes del número real.
5. Agregar el método de pago.
6. Poner en `.env.production` `SEED_PHONE_NUMBER_ID=<identificador del número real>` y ejecutar
   `deploy.sh`. El seed agrega el número nuevo sin borrar el de prueba.
7. Hacer la verificación del negocio (Paso 3 de Meta).

## Cómo sabemos que terminó
Un número que no está en la lista de prueba escribe al número real y el bot le responde.
En el panel se ven los estados Entregado y Leído.
