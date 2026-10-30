from core.types import JSONDict


class CatalogSearchCascade:
    """Busqueda determinista en cascada.

    Orden: normalizar, exacta, referencia cruzada, prefijo, trigrama, semantica, aplicacion.
    """

    async def search(self, query: str) -> list[JSONDict]:
        raise NotImplementedError("Pendiente: Fase 3 (docs/05-plan-mejoras.md)")
