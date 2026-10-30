#!/bin/sh
# Crea o actualiza el rol con el que se conecta la app (API y worker).
#
# Ese rol NO es superusuario, NO tiene BYPASSRLS y NO es dueno de las tablas,
# asi que las reglas de aislamiento por cliente (RLS) se le aplican siempre.
# Las migraciones las corre el dueno de las tablas (POSTGRES_USER).
#
# Es idempotente. Se ejecuta:
#   - solo, al crear el volumen de Postgres (docker-entrypoint-initdb.d), y
#   - en cada arranque desde botConfigurable.bat, para volumenes ya existentes:
#       docker compose exec -T db sh /docker-entrypoint-initdb.d/10-app-role.sh
set -e

: "${APP_DB_USER:=bot_app}"
: "${APP_DB_PASSWORD:?Falta APP_DB_PASSWORD}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_user="$APP_DB_USER" -v app_password="$APP_DB_PASSWORD" -v owner="$POSTGRES_USER" <<'SQL'
SELECT format('CREATE ROLE %I', :'app_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user') \gexec

ALTER ROLE :"app_user" WITH LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE
  PASSWORD :'app_password';

GRANT CONNECT ON DATABASE :"DBNAME" TO :"app_user";
GRANT USAGE ON SCHEMA public TO :"app_user";

-- Tablas y secuencias que ya existen...
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"app_user";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO :"app_user";

-- ...y las que creen las migraciones en el futuro.
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"app_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO :"app_user";

-- La tabla de control de alembic es solo para las migraciones.
SELECT format('REVOKE ALL ON TABLE alembic_version FROM %I', :'app_user')
WHERE to_regclass('public.alembic_version') IS NOT NULL \gexec
SQL

echo "Rol de la app '$APP_DB_USER' listo (sin superusuario ni BYPASSRLS)."
