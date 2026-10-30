# Guía de despliegue - botConfigurable

## Requisitos
- Docker y Docker Compose
- Cloudflare Tunnel (cloudflared) con cuenta
- Cuenta Meta Business con WABA verificado
- (Opcional) Ollama local para IA sin coste
- (Opcional) Cuentas Google/Microsoft/GoHighLevel

## 1. Clonar y configurar
```bash
git clone <repo> botConfigurable
cd botConfigurable
cp .env.example .env
```

Editar `.env` con valores reales:
- `DATABASE_URL` (rol de la app `bot_app`, sin privilegios: así se aplica RLS), `DATABASE_OWNER_URL` (dueño de las tablas, solo para migraciones), `REDIS_URL`
- `APP_DB_PASSWORD`: contraseña del rol `bot_app` (lo crea `infra/db/10-app-role.sh`). Va como variable de entorno al ejecutar `docker compose` y debe coincidir con la de `DATABASE_URL`
- `SECRET_KEY` (generar con `openssl rand -hex 32`)
- `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`
- Credenciales de proveedores

## 2. Levantar servicios con Docker
```bash
docker compose -f infra/docker-compose.yml up -d --build
```

Servicios: `api:8000`, `worker`, `db:5432`, `redis:6379`, `minio:9000/9001`

## 3. Migraciones
```bash
docker compose exec api alembic upgrade head
```

## 4. Sembrar datos demo
```bash
docker compose exec api python -m scripts.seed --demo
```

## 5. Configurar Cloudflare Tunnel
```bash
cloudflared tunnel login
cloudflared tunnel create botconfigurable
cloudflared tunnel route dns botconfigurable tu-dominio.com
```

Copiar `config.yml` a `infra/cloudflared/config.yml` con tunnel ID y credenciales.

Levantar tunnel:
```bash
docker run -d --name cloudflared --network botconfigurable_default \
  -v $(pwd)/infra/cloudflared:/etc/cloudflared \
  cloudflare/cloudflared:latest tunnel run
```

## 6. Configurar Webhook en Meta
- URL: `https://tu-dominio.com/webhook/whatsapp`
- Verify Token: valor de `WHATSAPP_VERIFY_TOKEN`
- Suscribirse a `messages`

## 7. Levantar Frontend (desarrollo)
```bash
cd apps/web
pnpm install
pnpm dev
```

Frontend en `http://localhost:5173`

## 8. Frontend (producción)
```bash
cd apps/web
pnpm build
# Servir dist/ con Caddy/Nginx
```

Caddy ya configurado en `Caddyfile` para servir API tras `/api` o directo.

## 9. Verificación
```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
curl http://localhost:8000/metrics
```

## Troubleshooting
- **Firma inválida**: verificar `WHATSAPP_APP_SECRET` y que el proxy no reescriba body
- **RLS**: siempre usar `tenant_session` o header `X-Tenant-ID` con `get_tenant_session`
- **Duplicados**: verificar idempotencia por `provider_message_id`
- **Ventana 24h**: usar plantillas aprobadas fuera de ventana
- **Grupos OBA**: requiere Official Business Account y aprobación Meta

## Comandos útiles
```bash
# Logs
docker compose logs -f api worker

# Tests
pytest -q -o addopts=""

# Migración nueva
alembic revision --autogenerate -m "descripcion"
```
