from fastapi import APIRouter

router = APIRouter()


@router.get("/campaigns")
async def list_campaigns() -> dict:
    return {"items": []}
