"""Composition root de la mensajeria: arma el worker a partir de la configuracion.

Lo usan apps/worker/main.py y los tests (con su propio adaptador).
"""

from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from consent.service import ConsentService
from core.config import Settings
from core.tenant_directory import TenantDirectory
from flows.engine.fsm import FlowEngine, NodeHandler
from flows.engine.instance_store import FlowInstanceStore
from flows.nodes.answer import AnswerHandler
from flows.nodes.menu import MenuHandler
from messaging.adapters.fake import FakeChannelAdapter
from messaging.adapters.whatsapp_cloud import WhatsAppCloudAdapter
from messaging.conversation_store import ConversationStore
from messaging.dead_letter import DeadLetterService
from messaging.inbound_processor import ConsentReplies, InboundProcessor
from messaging.outbox import OutboxWriter
from messaging.outbox_sender import OutboxSender, RetryPolicy
from messaging.ports.channel import ChannelAdapter
from messaging.send_policy import MessagingWindowRule, RuleBasedPolicy, SuppressionRule
from messaging.worker_cycle import WorkerCycle
from packs.loader import PackLoader

NODE_HANDLERS: dict[str, NodeHandler] = {"menu": MenuHandler(), "answer": AnswerHandler()}


def build_channel_adapter(settings: Settings, http_client: httpx.AsyncClient) -> ChannelAdapter:
    if settings.whatsapp_send_mode == "real":
        return WhatsAppCloudAdapter(
            http_client,
            base_url=settings.whatsapp_api_base_url,
            api_version=settings.meta_api_version,
            access_token=settings.whatsapp_access_token,
        )
    return FakeChannelAdapter()


def build_worker_cycle(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    adapter: ChannelAdapter,
) -> WorkerCycle:
    conversations = ConversationStore()
    inbound = InboundProcessor(
        conversations=conversations,
        flow=PackLoader().load_flow(Path(settings.flow_path)),
        engine=FlowEngine(NODE_HANDLERS),
        instances=FlowInstanceStore(),
        outbox=OutboxWriter(),
        consent=ConsentService(settings.opt_out_keyword_set, settings.opt_in_keyword_set),
        consent_replies=ConsentReplies(
            opt_out=settings.opt_out_confirmation_text, opt_in=settings.opt_in_confirmation_text
        ),
    )
    sender = OutboxSender(
        adapter=adapter,
        policy=RuleBasedPolicy([SuppressionRule(), MessagingWindowRule(settings.messaging_window)]),
        conversations=conversations,
        dead_letters=DeadLetterService(),
        retry=RetryPolicy(max_attempts=settings.outbox_max_attempts),
    )
    return WorkerCycle(session_factory, TenantDirectory(), inbound, sender)
