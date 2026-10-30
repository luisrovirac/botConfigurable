from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import TenantMixin, TimestampMixin
from core.types import JSONDict


class Catalog(Base, TenantMixin, TimestampMixin):
    __tablename__ = "catalog"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String)
    schema_json: Mapped[JSONDict] = mapped_column(JSONB, default=dict)


class CatalogItem(Base, TenantMixin, TimestampMixin):
    __tablename__ = "catalog_item"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    catalog_id: Mapped[UUID] = mapped_column(ForeignKey("catalog.id"))
    sku: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    attributes: Mapped[JSONDict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))


class ItemIdentifier(Base, TenantMixin):
    __tablename__ = "item_identifier"
    __table_args__ = (Index("ix_item_identifier_normalized", "value_normalized"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("catalog_item.id"))
    kind: Mapped[str] = mapped_column(String)  # sku, oem, npc, alias_proveedor, upc
    value: Mapped[str] = mapped_column(String)
    value_normalized: Mapped[str] = mapped_column(String)


class ItemFitment(Base, TenantMixin):
    __tablename__ = "item_fitment"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("catalog_item.id"))
    brand: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    year_from: Mapped[int]
    year_to: Mapped[int]
    engine: Mapped[str | None] = mapped_column(String)


class ItemMedia(Base, TenantMixin):
    __tablename__ = "item_media"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("catalog_item.id"))
    url: Mapped[str] = mapped_column(String)
    is_primary: Mapped[bool] = mapped_column(server_default=text("false"))
