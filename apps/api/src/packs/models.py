from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import TenantMixin


class Pack(Base):
    __tablename__ = "pack"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


class PackVersion(Base):
    __tablename__ = "pack_version"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    pack_id: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft")  # draft/validated/published
    checksum: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TenantPackBinding(Base, TenantMixin):
    __tablename__ = "tenant_pack_binding"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    pack_id: Mapped[str] = mapped_column(String, nullable=False)
    pack_version: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(String, default="true")  # simplified
