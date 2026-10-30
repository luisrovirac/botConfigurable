from fastapi import APIRouter

router = APIRouter()


@router.get("/appointments")
async def list_appointments() -> dict:
    return {"items": []}
