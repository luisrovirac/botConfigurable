#!/bin/sh
# Crea .env.production con secretos aleatorios. Se corre UNA vez en el servidor.
#   sh scripts/init-env-production.sh admin@tudominio.com
# No sobrescribe un .env.production existente (perderias las contrasenas de la base).
set -e
cd "$(dirname "$0")/.."

FILE=.env.production
ADMIN_EMAIL="${1:?Uso: sh scripts/init-env-production.sh EMAIL_DEL_ADMIN}"

if [ -f "$FILE" ]; then
  echo "$FILE ya existe; no se toca. Editalo a mano si hace falta." >&2
  exit 1
fi

secret() { openssl rand -hex "$1"; }

VERIFY_TOKEN=$(secret 16)
ADMIN_PASSWORD=$(secret 12)

umask 077
cat > "$FILE" <<EOF
# Produccion de botConfigurable. Generado el $(date -u +%Y-%m-%dT%H:%M:%SZ).
# NO lo subas a git (esta en .gitignore). Guarda una copia segura de las contrasenas.

# Puerto local que publica Caddy (la route de Cloudflare apunta a http://localhost:WEB_PORT).
WEB_PORT=8030

# Base de datos (solo letras y numeros: van dentro de URLs).
POSTGRES_PASSWORD=$(secret 24)
APP_DB_PASSWORD=$(secret 24)

LOG_LEVEL=INFO
SECRET_KEY=$(secret 32)

# --- WhatsApp Cloud API (Meta) ---
# Token de verificacion: copialo tal cual en Meta (Webhooks -> Token de verificacion).
WHATSAPP_VERIFY_TOKEN=$VERIFY_TOKEN
# Meta -> Configuracion de la app -> Basica -> Clave secreta de la app.
WHATSAPP_APP_SECRET=PEGAR_APP_SECRET_DE_META
# Meta -> WhatsApp -> Configuracion de la API -> Identificador del numero de telefono.
SEED_PHONE_NUMBER_ID=PEGAR_PHONE_NUMBER_ID_DE_META
# fake: no envia a Meta (solo registra). Cambia a real cuando tengas WHATSAPP_ACCESS_TOKEN.
WHATSAPP_SEND_MODE=fake
WHATSAPP_ACCESS_TOKEN=
META_API_VERSION=v21.0

# --- Usuario administrador del panel (se crea en el primer despliegue) ---
SEED_ADMIN_EMAIL=$ADMIN_EMAIL
SEED_ADMIN_PASSWORD=$ADMIN_PASSWORD
EOF

echo "Creado $FILE (permisos 600)."
echo
echo "  Token de verificacion para Meta: $VERIFY_TOKEN"
echo "  Panel: $ADMIN_EMAIL / $ADMIN_PASSWORD"
echo
echo "Falta completar en $FILE: WHATSAPP_APP_SECRET y SEED_PHONE_NUMBER_ID."
