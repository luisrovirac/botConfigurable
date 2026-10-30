from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_auth_service, get_current_principal, get_session
from auth.service import AuthenticationError, AuthService, Principal, TokenPair

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    @classmethod
    def from_pair(cls, pair: TokenPair) -> "TokenResponse":
        return cls(access_token=pair.access_token, refresh_token=pair.refresh_token)


class MeResponse(BaseModel):
    user_id: UUID
    tenant_id: str
    role: str


@router.post("/login")
async def login(
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    try:
        pair = await auth.login(session, body.email, body.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return TokenResponse.from_pair(pair)


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    try:
        pair = await auth.refresh(session, body.refresh_token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return TokenResponse.from_pair(pair)


@router.get("/me")
async def me(principal: Annotated[Principal, Depends(get_current_principal)]) -> MeResponse:
    return MeResponse(user_id=principal.user_id, tenant_id=principal.tenant_id, role=principal.role)
