@echo off
REM botConfigurable.bat - Arranca el entorno LOCAL de botConfigurable:
REM   - Docker Desktop + contenedores: api (FastAPI), worker, PostgreSQL, Redis, MinIO
REM   - Migraciones de base de datos (alembic upgrade head)
REM   - Frontend React/Vite en modo desarrollo (recarga sola al guardar)
REM   - Navegador con el frontend, la documentacion de la API (/docs) y la consola de MinIO
REM   - cmd en la raiz para git/pytest y VS Code
REM
REM Puertos: se usan puertos distintos a los de por defecto porque 8000 y 6379
REM ya los ocupan otros contenedores de esta PC (services-caddy, etc.).
REM   API      http://localhost:8010   (docs: /docs, salud: /healthz)
REM   Frontend http://localhost:5173
REM   MinIO    http://localhost:9011   (minioadmin / minioadmin)
REM   Postgres localhost:5442          (base botconfigurable)
REM            app: bot_app / bot_app_dev (sin privilegios, sujeto a RLS)
REM            dueno/migraciones: user / password
REM   Redis    localhost:6389
REM
REM Para apagar todo: scripts\dev-stop.bat   Para ver logs: scripts\dev-logs.bat
REM Respaldo de la version anterior: backup_pre_bat\botConfigurable.bat

set ROOT=C:\Users\User\Projects\SaxNew\botConfigurable
set WEB=%ROOT%\apps\web
set COMPOSE=docker compose -f "%ROOT%\infra\docker-compose.yml"
set DOCKER_EXE=C:\Program Files\Docker\Docker\Docker Desktop.exe
set CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
if not exist "%CHROME%" set CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe

REM Puertos del host (docker-compose.yml los lee de estas variables)
set API_PORT=8010
set DB_PORT=5442
set REDIS_PORT=6389
set MINIO_PORT=9010
set MINIO_CONSOLE_PORT=9011
set WEB_PORT=5173

REM Cada ventana vuelve a llamar a este mismo archivo con su seccion.
if "%~1"==":services" goto services
if "%~1"==":web" goto web

REM ===================== Ventana principal =====================
start "BOT SERVICIOS (docker)" cmd /k call "%~f0" :services
start "BOT WEB (vite)" cmd /k call "%~f0" :web

REM cmd en la raiz para git / pytest, y VS Code
start "BOT git" cmd /k "cd /d %ROOT%"
start "code" cmd /c "cd /d %ROOT% && code ."

echo Esperando a que la API responda en http://localhost:%API_PORT%/healthz ...
echo (la primera vez tarda varios minutos: se construye la imagen de Docker)
:waitapi
timeout /t 3 /nobreak >nul
curl -s -f -o nul http://localhost:%API_PORT%/healthz
if errorlevel 1 goto waitapi

echo Esperando al frontend en http://localhost:%WEB_PORT% ...
:waitweb
timeout /t 2 /nobreak >nul
curl -s -f -o nul http://localhost:%WEB_PORT%
if errorlevel 1 goto waitweb

if exist "%CHROME%" (
  start "" "%CHROME%" --incognito "http://localhost:%WEB_PORT%" "http://localhost:%API_PORT%/docs" "http://localhost:%MINIO_CONSOLE_PORT%"
) else (
  start "" "http://localhost:%WEB_PORT%"
  start "" "http://localhost:%API_PORT%/docs"
  start "" "http://localhost:%MINIO_CONSOLE_PORT%"
)
echo.
echo Listo. Entorno botConfigurable iniciado.
echo   Frontend  http://localhost:%WEB_PORT%
echo   API docs  http://localhost:%API_PORT%/docs
echo   MinIO     http://localhost:%MINIO_CONSOLE_PORT%  (minioadmin / minioadmin)
timeout /t 8 >nul
exit /b

REM ===================== Servicios Docker =====================
:services
cd /d "%ROOT%"
docker info >nul 2>&1
if not errorlevel 1 goto dockerok
echo Iniciando Docker Desktop...
start "" "%DOCKER_EXE%"
:waitdocker
timeout /t 3 /nobreak >nul
docker info >nul 2>&1
if errorlevel 1 goto waitdocker
:dockerok

REM .env local: se crea desde .env.example apuntando a los contenedores db y redis.
if exist "%ROOT%\.env" goto envok
echo Creando .env local a partir de .env.example...
powershell -NoProfile -Command "(Get-Content '%ROOT%\.env.example') -replace '@localhost:5432', '@db:5432' -replace 'redis://localhost:6379', 'redis://redis:6379' -replace '^SECRET_KEY=.*', ('SECRET_KEY=' + [guid]::NewGuid().ToString('N')) | Set-Content -Encoding ascii '%ROOT%\.env'"
:envok
REM .env de antes del rol bot_app: la app se conectaba como superusuario.
findstr /b /c:"DATABASE_OWNER_URL=" "%ROOT%\.env" >nul
if not errorlevel 1 goto envrole
echo Actualizando .env: la app pasa a conectarse con el rol bot_app...
powershell -NoProfile -Command "$f='%ROOT%\.env'; (Get-Content $f) | ForEach-Object { if ($_ -match '^DATABASE_URL=(.*)//user:password@(.*)$') { 'DATABASE_URL=' + $matches[1] + '//bot_app:bot_app_dev@' + $matches[2]; 'DATABASE_OWNER_URL=' + $matches[1] + '//user:password@' + $matches[2] } else { $_ } } | Set-Content -Encoding ascii $f"
:envrole

REM Si un puerto ya esta ocupado por otro proceso, avisar y esperar.
for %%P in (%API_PORT% %DB_PORT% %REDIS_PORT% %MINIO_PORT% %MINIO_CONSOLE_PORT%) do call :chkport %%P
goto portsok

:chkport
%COMPOSE% ps --format "{{.Ports}}" 2>nul | findstr /c:":%1->" >nul
if not errorlevel 1 goto :eof
netstat -ano | findstr /r /c:"TCP.*:%1 .*LISTENING" >nul
if errorlevel 1 goto :eof
echo.
echo ATENCION: el puerto %1 ya esta ocupado por otro proceso (PID al final):
netstat -ano | findstr /r /c:"TCP.*:%1 .*LISTENING"
echo Cierralo o cambia el puerto arriba en este .bat, y pulsa una tecla para reintentar.
pause
goto chkport

:portsok
echo Levantando contenedores (api, worker, db, redis, minio)...
%COMPOSE% up -d --build
if errorlevel 1 (
  echo No se pudieron levantar los contenedores. Revisa los errores de arriba.
  goto :eof
)

echo Esperando a PostgreSQL...
:waitdb
timeout /t 2 /nobreak >nul
%COMPOSE% exec -T db pg_isready -U user >nul 2>&1
if errorlevel 1 goto waitdb

echo Preparando el rol sin privilegios de la app (bot_app)...
%COMPOSE% exec -T db sh /docker-entrypoint-initdb.d/10-app-role.sh
if errorlevel 1 echo ATENCION: no se pudo preparar el rol bot_app. Revisa el error de arriba.

echo Aplicando migraciones (alembic upgrade head)...
%COMPOSE% exec -T api alembic upgrade head
if errorlevel 1 echo ATENCION: las migraciones fallaron. Revisa el error de arriba.

echo.
echo Servicios arriba. API: http://localhost:%API_PORT%/docs
echo Tras cambiar codigo Python: %COMPOSE% restart api worker
echo Mostrando logs de api y worker (Ctrl+C para dejar de verlos; los contenedores siguen):
echo.
%COMPOSE% logs -f --tail 50 api worker
goto :eof

REM ===================== Frontend (Vite) =====================
:web
cd /d "%WEB%"
if not exist node_modules call npm install
call npm run dev -- --port %WEB_PORT% --strictPort
goto :eof
