from fastapi import APIRouter

router = APIRouter()


@router.get("/catalog/search")
async def search_catalog(q: str = "") -> dict:
    return {"results": []}
