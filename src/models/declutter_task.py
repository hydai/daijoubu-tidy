from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class DeclutterTask(Base, UUIDMixin, TimestampMixin):
    """斷捨離任務 - 儲存物品分析結果和處理狀態"""

    __tablename__ = "declutter_tasks"

    # 物品資訊
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI 分析結果
    analysis: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # keep, consider, discard

    # 任務狀態
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, done, dismissed

    # 實際處理結果
    action_taken: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Discord 來源資訊
    source_channel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_message_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
