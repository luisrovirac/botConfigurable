# ADR 0003: Estado real de la Fase 0

Fecha: 2026-10-30

## Estado
Aceptado. Reemplaza al ADR 0002.

## Contexto
El ADR 0002 y el CHANGELOG 0.1.0 daban la Fase 0 por terminada. Una revisión completa del
código (2026-10-30, ver `docs/05-plan-mejoras.md`) mostró otra cosa:

- El webhook de WhatsApp respondía 500 siempre: importaba `SessionLocal` cuando aún valía `None`.
- `SET LOCAL app.tenant_id = :param` no es SQL válido con parámetros.
- Los modelos ORM tenían columnas que no existían en la base.
- La verificación de Meta nunca pasaba: faltaban los alias `hub.*`.
- El worker escribía un log y terminaba, y el adaptador de WhatsApp no enviaba nada.
- Los tests eran `assert True` o búsquedas de texto, y el CI fallaba en la instalación.
- La mayoría de los módulos eran stubs que devolvían datos inventados.

## Decisión
- La Fase 0 se considera **no terminada**. Se completa en dos etapas:
  - **Etapa 1:** base estándar y corrección de bugs.
  - **Etapa 2:** el walking skeleton real, con el criterio de aceptación del plan maestro §7.
- Un ADR solo declara terminada una fase si su criterio de aceptación se demostró con tests
  automáticos que pasan en CI.
- Los stubs de fases futuras no devuelven datos falsos: lanzan `NotImplementedError` indicando
  la fase.

## Consecuencias
- El CHANGELOG distingue lo implementado de lo planificado.
- El estado de cada etapa se lleva en `docs/05-plan-mejoras.md`.
