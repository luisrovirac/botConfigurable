@echo off
REM Ver logs de la API y el worker de botConfigurable (Ctrl+C para salir; los contenedores siguen).
cd /d "%~dp0.."
call "%~dp0dev-ports.bat"
docker compose -f infra\docker-compose.yml logs -f --tail 100 api worker
