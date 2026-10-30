from fastapi import APIRouter, HTTPException, status

router = APIRouter(tags=["auth"])


@router.post("/auth/login")
async def login() -> None:
    """Pendiente (Etapa 2, plan docs/05-plan-mejoras.md 2.7).

    Antes devolvia tokens falsos; ahora responde 501 para que nadie lo confunda con un login real.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Login aun no implementado"
    )
