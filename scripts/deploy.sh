#!/bin/sh
# Despliega o actualiza botConfigurable en el servidor (idempotente).
#   sh scripts/deploy.sh
# Construye las imagenes, aplica migraciones y seed, y levanta api, worker y web.
set -e
cd "$(dirname "$0")/.."

ENV_FILE=.env.production
COMPOSE="docker compose --env-file $ENV_FILE -f infra/docker-compose.prod.yml"

if [ ! -f "$ENV_FILE" ]; then
  echo "Falta $ENV_FILE. Crealo con: sh scripts/init-env-production.sh EMAIL_DEL_ADMIN" >&2
  exit 1
fi
if grep -q "PEGAR_" "$ENV_FILE"; then
  echo "Completa los valores PEGAR_... de $ENV_FILE antes de desplegar." >&2
  exit 1
fi

WEB_PORT=$(grep -E '^WEB_PORT=' "$ENV_FILE" | cut -d= -f2)
WEB_PORT=${WEB_PORT:-8030}

echo "== Construyendo imagenes (la primera vez tarda unos minutos)"
$COMPOSE build api web

echo "== Levantando (migraciones y seed primero, luego api, worker y web)"
$COMPOSE up -d --no-build --remove-orphans --wait

echo "== Migraciones y seed"
$COMPOSE logs --no-log-prefix migrate | tail -n 5

echo "== Estado"
$COMPOSE ps

echo "== Verificacion local"
curl -fsS "http://127.0.0.1:$WEB_PORT/readyz" && echo
echo "Listo. Route de Cloudflare: http://localhost:$WEB_PORT"
