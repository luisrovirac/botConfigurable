# Guía de despliegue - botConfigurable

> **Estado (2026-10-30):** el proyecto todavía no está listo para producción. Faltan:
> - El compose de producción.
> - Caddy y cloudflared como servicios.
> - El worker con envío real (Etapa 2).
> - El seed de datos.
>
> Ver la sección "Transversal" de `docs/05-plan-mejoras.md`. Esta guía describe lo que existe
> hoy y marca lo que está pendiente.

## Requisitos
- Docker y Docker Compose.
- Cuenta de Meta Business con WABA verificado (para WhatsApp real).
- Cloudflare Tunnel (cloudflared) para exponer el webhook.

## 1. Configurar
```bash
git clone <repo> botConfigurable
cd botConfigurable
cp .env.example .env
```

Editar `.env` (el archivo explica cada variable). Fuera de `development`/`test` la app no
arranca sin:
- `ENVIRONMENT=production` y `SECRET_KEY` de al menos 32 caracteres aleatorios
  (`openssl rand -hex 32`).
- `WHATSAPP_VERIFY_TOKEN` y `WHATSAPP_APP_SECRET` reales.
- `DATABASE_URL` con el rol de la app (`bot_app`, sin privilegios: así se aplica RLS).
- `DATABASE_OWNER_URL` con el dueño de las tablas (solo para migraciones).

`APP_DB_PASSWORD` es la contraseña de `bot_app`. Se pasa como variable de entorno al ejecutar
`docker compose` y debe coincidir con la de `DATABASE_URL`.

## 2. Imagen
La imagen de producción es la etapa `runtime`: sin herramientas de desarrollo y con usuario
no-root.
```bash
docker build -f infra/Dockerfile.api --target runtime -t botconfigurable-api .
```
`infra/docker-compose.yml` es el entorno de **desarrollo**: usa la etapa `dev`, monta el código
y recarga sola. *Pendiente:* `infra/docker-compose.prod.yml`.

## 3. Base de datos
1. Crear el rol de la app y la base de tests (idempotente; en compose corre solo al crear el
   volumen):
   ```bash
   docker compose -f infra/docker-compose.yml exec -T db sh /docker-entrypoint-initdb.d/10-app-role.sh
   ```
2. Migraciones. Corren como dueño, y la 0006 da los permisos a `bot_app`:
   ```bash
   docker compose -f infra/docker-compose.yml exec -T api alembic upgrade head
   ```

*Pendiente (Etapa 2):* `scripts/seed.py --demo` (inquilino, cuenta de canal y usuario admin).

## 4. Webhook de Meta
- URL: `https://tu-dominio.com/webhook/whatsapp`
- Verify Token: el valor de `WHATSAPP_VERIFY_TOKEN`.
- Suscribirse a `messages`.

*Pendiente (Etapa 2):* hoy todos los mensajes van al inquilino `WHATSAPP_DEFAULT_TENANT_ID`. La
Etapa 2 resuelve el inquilino por `channel_account` (`phone_number_id`).

Túnel de prueba (sin dominio propio):
```bash
cloudflared tunnel --url http://localhost:8010
```

## 5. Frontend
```bash
cd apps/web
npm ci
npm run build   # genera dist/
```
*Pendiente:* servir `dist/` y la API detrás de Caddy (`Caddyfile` hoy solo hace proxy a la API).

## 6. Verificación
```bash
curl http://localhost:8010/healthz   # proceso vivo
curl http://localhost:8010/readyz    # base y Redis responden (503 si no)
curl http://localhost:8010/metrics
```

## Problemas comunes
- **403 en el webhook:** la firma no coincide. Revisar `WHATSAPP_APP_SECRET` y que ningún proxy
  reescriba el cuerpo.
- **La app no ve datos:** con RLS, cada transacción debe fijar el inquilino
  (`core.tenant.set_tenant`). Sin inquilino no se ve ninguna fila, y es intencional.
- **Duplicados:** el webhook es idempotente por `(tenant_id, provider_message_id)`.
- **Falla el test que compara modelos y base:** falta una migración para un cambio de modelo.
