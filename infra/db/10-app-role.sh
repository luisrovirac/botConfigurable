#!/bin/sh
# Crea o actualiza el rol con el que se conecta la app (API y worker) y, en desarrollo,
# la base de tests.
#
# Ese rol NO es superusuario, NO tiene BYPASSRLS y NO es dueno de las tablas,
# asi que las reglas de aislamiento por cliente (RLS) se le aplican siempre.
# Sus permisos sobre las tablas los da la migracion 0006 (igual en todas las bases).
#
# Es idempotente. Se ejecuta:
#   - solo, al crear el volumen de Postgres (docker-entrypoint-initdb.d), y
#   - en cada arranque desde botConfigurable.bat, para volumenes ya existentes:
#       docker compose exec -T db sh /docker-entrypoint-initdb.d/10-app-role.sh
#   - en CI, contra el service container (con PGHOST y PGPASSWORD definidos).
# En produccion CREATE_TEST_DB=false: no se crea la base de tests.
set -e

: "${APP_DB_USER:=bot_app}"
: "${APP_DB_PASSWORD:?Falta APP_DB_PASSWORD}"
: "${CREATE_TEST_DB:=true}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_user="$APP_DB_USER" -v app_password="$APP_DB_PASSWORD" -v main_db="$POSTGRES_DB" <<'SQL'
SELECT format('CREATE ROLE %I', :'app_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user') \gexec

ALTER ROLE :"app_user" WITH LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE
  PASSWORD :'app_password';

GRANT CONNECT ON DATABASE :"main_db" TO :"app_user";
SQL

if [ "$CREATE_TEST_DB" = "true" ]; then
  TEST_DB="${POSTGRES_DB}_test"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -v app_user="$APP_DB_USER" -v test_db="$TEST_DB" <<'SQL'
SELECT format('CREATE DATABASE %I', :'test_db')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'test_db') \gexec

GRANT CONNECT ON DATABASE :"test_db" TO :"app_user";
SQL
  echo "Base de tests: $TEST_DB"
fi

echo "Rol de la app '$APP_DB_USER' listo (sin superusuario ni BYPASSRLS)."
