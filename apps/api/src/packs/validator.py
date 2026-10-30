from core.types import JSONDict


class PackValidator:
    """Valida un pack contra su esquema y sus transcripciones golden."""

    def validate(self, pack: JSONDict) -> bool:
        raise NotImplementedError("Pendiente: Fase 2 (docs/05-plan-mejoras.md)")
