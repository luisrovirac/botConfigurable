# ADR 0004: Decisiones de la Etapa 1 (base estándar)

Fecha: 2026-10-30

## Estado
Aceptado

## Contexto
La Etapa 1 del plan (`docs/05-plan-mejoras.md`) dejó el proyecto con herramientas, tests y CI
estándar. Varias decisiones no son obvias y conviene dejarlas escritas.

## Decisiones

### Dependencias con uv, sin empaquetar la app
`pyproject.toml` usa `[tool.uv] package = false` y `uv.lock`. La app no es una librería: uv
instala solo las dependencias y el código se importa desde `apps/api/src` (`PYTHONPATH` en
Docker, `pythonpath` en pytest, `mypy_path` en mypy). Así se evita el fallo de hatchling, que
no sabía qué carpetas empaquetar, y las builds son reproducibles.

### Todo el tooling de Python corre en Docker
El Python de la máquina de desarrollo es 3.10 y el proyecto usa 3.12. `scripts\test.bat` corre
formato, lint, tipos y tests en el servicio `tools` de compose. El CI usa el mismo
`scripts/check.sh`.

### Tests contra una base real y con el rol de la app
- Los tests usan la base `botconfigurable_test`. `conftest.py` se niega a correr contra otra.
- Las migraciones corren como dueño de las tablas y la app como `bot_app`, así que RLS se
  prueba de verdad.
- Los tests de arquitectura comprueban cosas reales:
  - Hay políticas en `pg_policies`.
  - Los modelos coinciden con la base (`compare_metadata`).
  - Las reglas de `RULES.md` se cumplen, revisadas sobre el AST.

### Permisos de `bot_app` en una migración
La migración 0006 da los permisos: lectura y escritura en tablas actuales y futuras, solo
lectura en las tablas globales `pack`/`pack_version`, y nada en `alembic_version`. Así quedan
iguales en desarrollo, tests, CI y producción. `infra/db/10-app-role.sh` solo crea el rol, su
contraseña y la base de tests. Una migración que cree otra tabla global debe revocar su
escritura.

### Unidad de trabajo en el punto de entrada
- La dependencia `get_session` abre una transacción por petición: commit si la ruta termina
  bien, rollback si falla.
- Los servicios nunca hacen commit (lo verifica un test de arquitectura).
- El inquilino se fija con `set_config('app.tenant_id', ..., true)` y dura hasta el fin de la
  transacción.

### Recursos compartidos en `lifespan`
`api.main.create_app()` es la composition root: crea el engine, la fábrica de sesiones y Redis
en el `lifespan` y los guarda en `app.state`. No hay globales mutables, y los tests crean la app
con su propia configuración.

### Servicios opcionales en perfiles de compose
- El worker está en el perfil `worker` hasta que tenga un bucle real (Etapa 2).
- MinIO está en el perfil `storage` porque ningún código lo usa todavía.
- Así no se reinician en bucle ni consumen recursos al arrancar.

## Consecuencias
- Cambiar el esquema obliga a crear una migración: si no, falla el test que compara los modelos
  con la base.
- Agregar un módulo de modelos obliga a registrarlo en `apps/api/src/db_models.py`.
