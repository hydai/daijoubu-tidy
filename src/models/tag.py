from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .item import Item


class Tag(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Relationships
    items: Mapped[list["Item"]] = relationship(
        secondary="item_tags",
        back_populates="tags",
    )
