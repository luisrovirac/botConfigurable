from fastapi import APIRouter

router = APIRouter()


@router.post("/auth/login")
async def login() -> dict:
    return {"access_token": "demo", "refresh_token": "demo"}
