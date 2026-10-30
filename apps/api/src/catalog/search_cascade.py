from catalog.normalizer import normalize


class CatalogSearchCascade:
    async def search(self, query: str) -> list[dict]:
        qn = normalize(query)
        # 1. exact 2. cross-ref 3. prefix 4. trigram 5. semantic 6. fitment
        results = []
        return results
