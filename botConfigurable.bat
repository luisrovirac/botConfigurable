@echo off
REM botConfigurable.bat - Arranca el entorno LOCAL de botConfigurable:
REM   - Docker Desktop + contenedores: api y worker (se recargan solos al guardar), PostgreSQL
REM   - Rol bot_app, base de tests, migraciones (alembic upgrade head) y datos demo (seed)
REM   - Frontend React/Vite en modo desarrollo (recarga sola al guardar)
REM   - Navegador con el frontend y la documentacion de la API (/docs)
REM   - cmd en la raiz para git y VS Code
REM
REM Puertos (definidos en scripts\dev-ports.bat; 8000 y 6379 ya los usan otros contenedores):
REM   API      http://localhost:8010   (docs: /docs, salud: /healthz, listo: /readyz)
REM   Frontend http://localhost:5173
REM   Postgres localhost:5442          (bases botconfigurable y botconfigurable_test)
REM            app: bot_app / bot_app_dev (sin privilegios, sujeto a RLS)
REM            dueno/migraciones: user / password
REM
REM Acceso al panel: admin@demo.local / demo-admin-2026 (lo crea scripts\seed.py)
REM Simular mensajes de WhatsApp: scripts\simulate.bat "Hola"   (sin credenciales de Meta)
REM Tests, lint y tipos: scripts\test.bat   Apagar: scripts\dev-stop.bat   Logs: scripts\dev-logs.bat
REM Opcional: MinIO -> docker compose --profile storage up -d

set ROOT=C:\Users\User\Projects\SaxNew\botConfigurable
set WEB=%ROOT%\apps\web
set COMPOSE=docker compose -f "%ROOT%\infra\docker-compose.yml"
set DOCKER_EXE=C:\Program Files\Docker\Docker\Docker Desktop.exe
set CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
if not exist "%CHROME%" set CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe

call "%ROOT%\scripts\dev-ports.bat"

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
  start "" "%CHROME%" --incognito "http://localhost:%WEB_PORT%" "http://localhost:%API_PORT%/docs"
) else (
  start "" "http://localhost:%WEB_PORT%"
  start "" "http://localhost:%API_PORT%/docs"
)
echo.
echo Listo. Entorno botConfigurable iniciado.
echo   Frontend  http://localhost:%WEB_PORT%
echo   API docs  http://localhost:%API_PORT%/docs
echo   Acceso    admin@demo.local / demo-admin-2026
echo   Probar    scripts\simulate.bat "Hola"   (simula un cliente de WhatsApp)
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

REM .env local: se crea desde .env.example apuntando al contenedor db.
if exist "%ROOT%\.env" goto envok
echo Creando .env local a partir de .env.example...
powershell -NoProfile -Command "(Get-Content '%ROOT%\.env.example') -replace '@localhost:5432', '@db:5432' -replace '^SECRET_KEY=.*', ('SECRET_KEY=' + [guid]::NewGuid().ToString('N')) | Set-Content -Encoding ascii '%ROOT%\.env'"
:envok
REM .env de antes del rol bot_app: la app se conectaba como superusuario.
findstr /b /c:"DATABASE_OWNER_URL=" "%ROOT%\.env" >nul
if not errorlevel 1 goto envrole
echo Actualizando .env: la app pasa a conectarse con el rol bot_app...
powershell -NoProfile -Command "$f='%ROOT%\.env'; (Get-Content $f) | ForEach-Object { if ($_ -match '^DATABASE_URL=(.*)//user:password@(.*)$') { 'DATABASE_URL=' + $matches[1] + '//bot_app:bot_app_dev@' + $matches[2]; 'DATABASE_OWNER_URL=' + $matches[1] + '//user:password@' + $matches[2] } else { $_ } } | Set-Content -Encoding ascii $f"
:envrole

REM Si un puerto ya esta ocupado por otro proceso, avisar y esperar.
for %%P in (%API_PORT% %DB_PORT%) do call :chkport %%P
goto portsok

:chkport
%COMPOSE% ps --format "{{.Ports}}" 2>nul | findstr /c:":%1->" >nul
if not errorlevel 1 goto :eof
netstat -ano | findstr /r /c:"TCP.*:%1 .*LISTENING" >nul
if errorlevel 1 goto :eof
echo.
echo ATENCION: el puerto %1 ya esta ocupado por otro proceso (PID al final):
netstat -ano | findstr /r /c:"TCP.*:%1 .*LISTENING"
echo Cierralo o cambia el puerto en scripts\dev-ports.bat, y pulsa una tecla para reintentar.
pause
goto chkport

:portsok
echo Levantando contenedores (api, db)...
%COMPOSE% up -d --build db api
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

echo Cargando datos demo (inquilino, numero de WhatsApp y usuario admin)...
%COMPOSE% exec -T api python scripts/seed.py --demo
if errorlevel 1 echo ATENCION: el seed fallo. Revisa el error de arriba.

REM El worker arranca despues de migrar: necesita las tablas y funciones al dia.
echo Levantando el worker...
%COMPOSE% up -d worker

echo.
echo Servicios arriba. API: http://localhost:%API_PORT%/docs
echo La API y el worker se recargan solos al guardar cambios en apps\.
echo Mostrando logs de la API y el worker (Ctrl+C para dejar de verlos; los contenedores siguen):
echo.
%COMPOSE% logs -f --tail 50 api worker
goto :eof

REM ===================== Frontend (Vite) =====================
:web
cd /d "%WEB%"
if not exist node_modules call npm install
call npm run dev -- --port %WEB_PORT% --strictPort
goto :eof
