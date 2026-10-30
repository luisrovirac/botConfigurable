from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import CreatedAtMixin, TenantMixin


class Pack(Base):
    """Catalogo global de packs (vertical de negocio). No es por inquilino: la app solo lee."""

    __tablename__ = "pack"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)


class PackVersion(Base, CreatedAtMixin):
    __tablename__ = "pack_version"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    pack_id: Mapped[str] = mapped_column(ForeignKey("pack.id"))
    version: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, server_default="draft")  # draft/validated/published
    checksum: Mapped[str | None] = mapped_column(String)


class TenantPackBinding(Base, TenantMixin):
    __tablename__ = "tenant_pack_binding"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    pack_id: Mapped[str] = mapped_column(ForeignKey("pack.id"))
    pack_version: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
