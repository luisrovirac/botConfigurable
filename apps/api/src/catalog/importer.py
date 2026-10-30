from core.types import JSONDict


class CatalogImporter:
    """Importacion de catalogo desde CSV/XLSX."""

    async def import_csv(self, path: str) -> JSONDict:
        raise NotImplementedError("Pendiente: Fase 3 (docs/05-plan-mejoras.md)")
