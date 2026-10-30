@echo off
REM Formato, lint, tipos y tests dentro de Docker (el Python local es 3.10; el proyecto usa 3.12).
REM Los tests usan la base botconfigurable_test, nunca la de desarrollo.
REM Argumentos extra van a pytest (rutas con /). Ejemplo: scripts\test.bat tests/unit -k jwt
setlocal
cd /d "%~dp0.."
call "%~dp0dev-ports.bat"
set COMPOSE=docker compose -f infra\docker-compose.yml

%COMPOSE% up -d --wait db
if errorlevel 1 exit /b 1
%COMPOSE% exec -T db sh /docker-entrypoint-initdb.d/10-app-role.sh >nul
if errorlevel 1 exit /b 1
%COMPOSE% --profile tools run --rm --build tools sh scripts/check.sh %*
