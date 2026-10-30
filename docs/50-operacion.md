# Operación

## Despliegue local
```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up -d --build
docker compose exec api alembic upgrade head
```
