# Despliegue en producción

Servidor de referencia: Ubuntu x86_64 con Docker 29 y Compose v5. `cloudflared` corre como
servicio del sistema y las routes se crean en el panel de Cloudflare.

Dirección pública: **https://botwhatsapp.devsax.site**. La route apunta a `http://localhost:8030`.

## Cómo queda

```
Meta / navegador ─HTTPS─> Cloudflare ─tunel─> cloudflared (servidor)
                                               └─> 127.0.0.1:8030  web (Caddy)
                                                     ├─ /api/*, /healthz, /readyz ─> api (FastAPI)
                                                     └─ todo lo demas ─> panel (React)
                    worker (cola de entrada y envios)  db (Postgres, sin puerto publicado)
```

- **Puerto:** solo se publica el 8030, y solo en `127.0.0.1`; nada queda abierto a la red.
- **Rutas que no se publican:** `/docs` y `/metrics`.
- **Archivos:** `infra/docker-compose.prod.yml` y `infra/web/` (Caddy y el panel compilado).

## Primer despliegue

### 1. Copiar el proyecto (desde la laptop)
Hasta que el repositorio tenga remoto, se copia el último commit empaquetado:
```
scripts\package.bat
scp botconfigurable.tar.gz luis@SERVIDOR:~/projects/
```
En el servidor:
```bash
mkdir -p ~/projects/botconfigurable
tar xzf ~/projects/botconfigurable.tar.gz -C ~/projects/botconfigurable
cd ~/projects/botconfigurable
```
Con un remoto de git, esto se reemplaza por `git clone` (y `git pull` para actualizar).

### 2. Generar la configuración (una sola vez)
```bash
sh scripts/init-env-production.sh tu-email@devsax.site
```
- Crea `.env.production` con contraseñas y claves aleatorias, legible solo por tu usuario.
- Muestra el **token de verificación** para Meta y la **contraseña del panel**. Guárdalos.
- **No lo vuelvas a ejecutar**: la contraseña de la base queda fijada al crearla.

Completa en `.env.production` los dos valores de Meta:
- `WHATSAPP_APP_SECRET`: en la app de Meta, Configuración → Básica → Clave secreta de la app.
- `SEED_PHONE_NUMBER_ID`: en WhatsApp → Configuración de la API, el identificador del número.

### 3. Desplegar
```bash
sh scripts/deploy.sh
```
- Construye las imágenes, migra la base, carga los datos iniciales y levanta todo.
- Termina mostrando `{"status":"ready","database":"ok"}`.
- La primera vez tarda unos minutos.

### 4. Route en Cloudflare
En Zero Trust → Networks → Tunnels → tu túnel → **Public hostnames** → Add:

| Campo | Valor |
|---|---|
| Subdomain | `botwhatsapp` |
| Domain | `devsax.site` |
| Path | (vacío) |
| Service type | `HTTP` |
| URL | `localhost:8030` |

Para comprobarlo, abre https://botwhatsapp.devsax.site: debe aparecer el login del panel.

### 5. Webhook en Meta
En la app de Meta, WhatsApp → Configuración → Webhooks (el "Paso 2" del asistente):
1. **URL de devolución de llamada:** `https://botwhatsapp.devsax.site/api/v1/webhook/whatsapp`
2. **Token de verificación:** el que mostró el paso 2 (`WHATSAPP_VERIFY_TOKEN` en
   `.env.production`).
3. Pulsa **Verificar y guardar**. Meta llama a la URL en ese momento, así que la app tiene que
   estar arriba.
4. En los campos del webhook, suscríbete a **messages**.

### 6. Enviar de verdad
Mientras `WHATSAPP_SEND_MODE=fake`, el bot recibe y procesa, pero las respuestas solo quedan en
el log del worker. Para que lleguen al teléfono:
1. En `.env.production` pon `WHATSAPP_SEND_MODE=real` y `WHATSAPP_ACCESS_TOKEN=<token>`.
   - El token temporal del panel de Meta dura 24 horas.
   - Para uno permanente, usa un *usuario del sistema* del Business Manager con los permisos
     `whatsapp_business_messaging` y `whatsapp_business_management`.
2. Aplica el cambio con `sh scripts/deploy.sh`.
3. Prueba según `docs/HUMAN_TEST_PLAN.md` ("Fase 0 con WhatsApp real").

## Actualizar
Copia la versión nueva (paso 1; el `tar` sobrescribe el código y no toca `.env.production`) y
ejecuta:
```bash
sh scripts/deploy.sh
```

## Operación
Para no repetir el comando completo, define este alias en el servidor:
```bash
alias botc='docker compose --env-file .env.production -f infra/docker-compose.prod.yml'
```

| Tarea | Comando (desde `~/projects/botconfigurable`) |
|---|---|
| Estado | `botc ps` |
| Logs | `botc logs -f --tail 100 api worker` |
| Reiniciar | `botc restart api worker` |
| Detener (los datos se conservan) | `botc down` |
| Respaldo de la base | `botc exec -T db pg_dump -U botowner -Fc botconfigurable > respaldo-$(date +%F).dump` |
| Comprobar que está listo | `curl -s http://127.0.0.1:8030/readyz` |

Los logs de Docker se rotan solos: 5 archivos de 10 MB por servicio.

## Problemas comunes
- **Meta dice que no pudo validar la URL:**
  - Revisa que `curl -s http://127.0.0.1:8030/readyz` responda en el servidor.
  - Revisa que la route apunte a `localhost:8030`.
  - El token pegado en Meta debe ser idéntico a `WHATSAPP_VERIFY_TOKEN`.
- **Llegan mensajes pero no aparecen en el panel:**
  - Busca `webhook_unknown_channel` en `botc logs api`. Si aparece, `SEED_PHONE_NUMBER_ID` no
    coincide con el número de Meta. Corrígelo y ejecuta `sh scripts/deploy.sh`.
  - Busca `Invalid signature` (403). Si aparece, revisa `WHATSAPP_APP_SECRET`.
- **No llega ningún webhook:** con la app sin publicar, Meta puede entregar solo los webhooks de
  prueba del panel. Si los mensajes reales de los números de prueba no llegan, hay que publicar
  la app (Meta pide una URL de política de privacidad).
- **El panel pide login a cada rato:** el token de acceso dura 15 minutos y se renueva solo
  mientras la pestaña está abierta.

## Pendiente para producción completa
Ver "Transversal" en `docs/05-plan-mejoras.md`:
- Tokens de Meta por cuenta, cifrados.
- Revocación de sesiones.
- Respaldos automáticos.
- Opcional: proteger el panel con Cloudflare Access, sin proteger la ruta
  `/api/v1/webhook/whatsapp`, que Meta debe poder llamar.
