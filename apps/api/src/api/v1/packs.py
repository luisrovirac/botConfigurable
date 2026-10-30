from fastapi import APIRouter

router = APIRouter()


@router.get("/packs")
async def list_packs() -> dict:
    return {"items": []}
