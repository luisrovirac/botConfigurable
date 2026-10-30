@echo off
REM Detener todos los servicios de botConfigurable (los datos de la base se conservan).
cd /d "%~dp0.."
call "%~dp0dev-ports.bat"
echo Deteniendo contenedores...
docker compose -f infra\docker-compose.yml --profile worker --profile storage --profile tools down
echo.
echo Servicios detenidos.
pause
