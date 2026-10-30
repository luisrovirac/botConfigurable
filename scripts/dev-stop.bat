@echo off
REM Detener servicios de botConfigurable

cd /d %~dp0\..
echo Deteniendo contenedores...
docker compose -f infra\docker-compose.yml down
echo.
echo Servicios detenidos.
pause
