class CatalogSearch:
    async def search(self, query: str) -> list[dict]:
        # Cascada determinista: normalize -> exact -> cross-ref -> prefix -> trigram -> semantic -> fitment
        return []
