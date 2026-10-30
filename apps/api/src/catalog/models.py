from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import TenantMixin, TimestampMixin


class Catalog(Base, TenantMixin, TimestampMixin):
    __tablename__ = "catalog"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    schema_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class CatalogItem(Base, TenantMixin, TimestampMixin):
    __tablename__ = "catalog_item"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    catalog_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("catalog.id"), nullable=False)
    sku: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ItemIdentifier(Base, TenantMixin):
    __tablename__ = "item_identifier"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("catalog_item.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # sku, oem, npc, alias_proveedor, upc
    value: Mapped[str] = mapped_column(String, nullable=False)
    value_normalized: Mapped[str] = mapped_column(String, nullable=False, index=True)


class ItemFitment(Base, TenantMixin):
    __tablename__ = "item_fitment"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("catalog_item.id"), nullable=False)
    brand: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    year_from: Mapped[int] = mapped_column(Integer, nullable=False)
    year_to: Mapped[int] = mapped_column(Integer, nullable=False)
    engine: Mapped[str | None] = mapped_column(String, nullable=True)


class ItemMedia(Base, TenantMixin):
    __tablename__ = "item_media"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("catalog_item.id"), nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
