from typing import TYPE_CHECKING
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .category import Category
    from .tag import Tag


class Item(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "items"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), default="text")
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_channel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_message_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    # Relationships
    categories: Mapped[list["Category"]] = relationship(
        secondary="item_categories",
        back_populates="items",
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary="item_tags",
        back_populates="items",
    )


class ItemCategory(Base):
    __tablename__ = "item_categories"

    item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class ItemTag(Base):
    __tablename__ = "item_tags"

    item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
