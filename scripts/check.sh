#!/bin/sh
# Verificacion completa: formato, lint, tipos y tests con cobertura.
# Lo usan scripts\test.bat (dentro de Docker) y el CI. Los argumentos extra van a pytest,
# por ejemplo: sh scripts/check.sh tests/unit -k jwt
set -e

echo "== ruff format"
ruff format --check .
echo "== ruff check"
ruff check .
echo "== mypy"
mypy
echo "== pytest"
pytest "$@"
