@echo off
REM Simula mensajes de WhatsApp contra la API local (sin credenciales de Meta).
REM Ejemplos:
REM   scripts\simulate.bat "Hola"
REM   scripts\simulate.bat "1" --from 5215550002222 --name "Otra persona"
REM   scripts\simulate.bat "Hola" --id wamid.prueba --repeat 2
REM   scripts\simulate.bat BAJA
REM Ayuda: scripts\simulate.bat --help
setlocal
cd /d "%~dp0.."
call "%~dp0dev-ports.bat"
docker compose -f infra\docker-compose.yml exec -T api python scripts/simulate_whatsapp.py %*
