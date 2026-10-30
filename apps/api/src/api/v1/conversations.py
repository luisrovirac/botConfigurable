from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_inbox_queries, get_tenant_session
from inbox.queries import InboxQueries
from inbox.schemas import ConversationSummary, MessageView

router = APIRouter(prefix="/conversations", tags=["inbox"])


@router.get("")
async def list_conversations(
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    inbox: Annotated[InboxQueries, Depends(get_inbox_queries)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[ConversationSummary]:
    """Conversaciones del inquilino, la de actividad mas reciente primero."""
    return await inbox.conversations(session, limit)


@router.get("/{conversation_id}/messages")
async def list_messages(
    conversation_id: UUID,
    session: Annotated[AsyncSession, Depends(get_tenant_session)],
    inbox: Annotated[InboxQueries, Depends(get_inbox_queries)],
) -> list[MessageView]:
    messages = await inbox.messages(session, conversation_id)
    if messages is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversacion no existe")
    return messages
