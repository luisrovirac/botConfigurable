@echo off
REM Espera a que Docker este activo y levanta los contenedores de botConfigurable

cd /d %~dp0\..
set COMPOSE_FILE=infra\docker-compose.yml

echo Esperando a que Docker Desktop arranque...
:wait
docker info >nul 2>&1
if errorlevel 1 (
    timeout /t 3 /nobreak >nul
    goto wait
)

echo Docker activo. Levantando contenedores...
docker compose -f %COMPOSE_FILE% up -d

echo.
echo Esperando servicios...
timeout /t 10 /nobreak >nul

echo Ejecutando migraciones...
docker compose -f %COMPOSE_FILE% exec -T api alembic upgrade head 2>nul || echo (migraciones pendientes o ya aplicadas)

echo.
echo Servicios levantados.
echo API: http://localhost:8000/healthz
echo MinIO Console: http://localhost:9001
echo.
pause
