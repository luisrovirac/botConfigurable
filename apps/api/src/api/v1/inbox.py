from fastapi import APIRouter

router = APIRouter()


@router.get("/inbox")
async def list_inbox() -> dict:
    return {"items": []}
