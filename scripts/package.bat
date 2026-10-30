@echo off
REM Empaqueta el ultimo commit para copiarlo al servidor (sin .env, node_modules ni basura).
REM Uso: scripts\package.bat   ->  crea botconfigurable.tar.gz en la raiz del proyecto.
REM Solo incluye lo que esta en git: haz commit antes de empaquetar.
setlocal
cd /d "%~dp0.."
git archive --format=tar.gz -o botconfigurable.tar.gz HEAD
if errorlevel 1 exit /b 1
echo Creado botconfigurable.tar.gz (commit actual):
git log -1 --oneline
echo.
echo Copialo al servidor, por ejemplo:
echo   scp botconfigurable.tar.gz luis@SERVIDOR:~/projects/
