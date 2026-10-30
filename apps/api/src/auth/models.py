from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import CreatedAtMixin, TenantMixin, TimestampMixin
from core.types import JSONDict


class User(Base, TenantMixin, TimestampMixin):
    __tablename__ = "user"
    __table_args__ = (UniqueConstraint("email", name="user_email_key"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    role: Mapped[str] = mapped_column(String, server_default="agent")


class TenantMembership(Base, TenantMixin, CreatedAtMixin):
    __tablename__ = "tenant_membership"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"))
    role: Mapped[str] = mapped_column(String)


class AuditLog(Base, TenantMixin, CreatedAtMixin):
    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user.id"))
    action: Mapped[str] = mapped_column(String)
    resource: Mapped[str | None] = mapped_column(String)
    meta: Mapped[JSONDict | None] = mapped_column(JSONB)
