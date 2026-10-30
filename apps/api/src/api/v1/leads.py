from fastapi import APIRouter

router = APIRouter()


@router.get("/leads")
async def list_leads() -> dict:
    return {"items": []}
