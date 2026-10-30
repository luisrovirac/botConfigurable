@echo off
REM Ver logs de botConfigurable

cd /d %~dp0\..
docker compose -f infra\docker-compose.yml logs -f api worker
