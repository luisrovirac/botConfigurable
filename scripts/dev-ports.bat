@echo off
REM Puertos del host para el entorno local (docker-compose.yml los lee de estas variables).
REM Son distintos a los de por defecto porque 8000 y 6379 ya los ocupan otros contenedores
REM de esta PC. Todos los .bat los toman de aqui para no recrear contenedores con otros puertos.
set API_PORT=8010
set DB_PORT=5442
set REDIS_PORT=6389
set MINIO_PORT=9010
set MINIO_CONSOLE_PORT=9011
set WEB_PORT=5173
