from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import String, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import DeclutterTask


class DeclutterTaskService:
    """Service for managing declutter tasks."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_task(
        self,
        item_name: str,
        analysis: str,
        decision: str,
        image_url: str | None = None,
        source_channel: str | None = None,
        source_message_id: str | None = None,
    ) -> DeclutterTask:
        """Create a new declutter task."""
        task = DeclutterTask(
            item_name=item_name,
            image_url=image_url,
            analysis=analysis,
            decision=decision,
            status="pending",
            source_channel=source_channel,
            source_message_id=source_message_id,
        )

        self.db.add(task)
        await self.db.flush()
        return task

    async def list_tasks(
        self,
        status: str | None = None,
        limit: int = 20,
    ) -> list[DeclutterTask]:
        """List declutter tasks with optional filtering."""
        query = select(DeclutterTask).order_by(DeclutterTask.created_at.desc())

        if status:
            query = query.where(DeclutterTask.status == status)

        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_task_by_id(self, task_id: UUID) -> DeclutterTask | None:
        """Get a task by its full ID."""
        result = await self.db.execute(
            select(DeclutterTask).where(DeclutterTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_task_by_prefix(self, id_prefix: str) -> DeclutterTask | None:
        """Get a task by ID prefix."""
        result = await self.db.execute(
            select(DeclutterTask).where(
                func.cast(DeclutterTask.id, String).like(f"{id_prefix}%")
            )
        )
        return result.scalar_one_or_none()

    async def update_task_status(
        self,
        id_prefix: str,
        status: str,
        action_taken: str | None = None,
    ) -> DeclutterTask | None:
        """Update a task's status."""
        task = await self.get_task_by_prefix(id_prefix)
        if not task:
            return None

        task.status = status
        if action_taken:
            task.action_taken = action_taken

        return task

    async def delete_task(self, id_prefix: str) -> bool:
        """Delete a task by ID prefix."""
        task = await self.get_task_by_prefix(id_prefix)
        if not task:
            return False

        await self.db.delete(task)
        return True

    async def get_pending_count(self) -> int:
        """Get count of pending tasks."""
        result = await self.db.execute(
            select(func.count(DeclutterTask.id)).where(
                DeclutterTask.status == "pending"
            )
        )
        return result.scalar() or 0

    async def get_stats(self) -> dict[str, int]:
        """Get task statistics."""
        result = await self.db.execute(
            select(DeclutterTask.status, func.count(DeclutterTask.id)).group_by(
                DeclutterTask.status
            )
        )
        stats = {row[0]: row[1] for row in result.all()}
        return {
            "pending": stats.get("pending", 0),
            "done": stats.get("done", 0),
            "dismissed": stats.get("dismissed", 0),
            "total": sum(stats.values()),
        }

    async def get_recent_completed(self, days: int = 7) -> int:
        """Get count of tasks completed in recent days."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.db.execute(
            select(func.count(DeclutterTask.id)).where(
                and_(
                    DeclutterTask.status == "done",
                    DeclutterTask.updated_at >= since,
                )
            )
        )
        return result.scalar() or 0

    async def get_recent_created(self, days: int = 7) -> int:
        """Get count of tasks created in recent days."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.db.execute(
            select(func.count(DeclutterTask.id)).where(
                DeclutterTask.created_at >= since
            )
        )
        return result.scalar() or 0

    async def get_completed_tasks(
        self, since: datetime | None = None, limit: int = 100
    ) -> list[DeclutterTask]:
        """Get completed tasks, optionally filtered by date."""
        query = (
            select(DeclutterTask)
            .where(DeclutterTask.status == "done")
            .order_by(DeclutterTask.updated_at.desc())
            .limit(limit)
        )

        if since:
            query = query.where(DeclutterTask.updated_at >= since)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_decision_stats(
        self, since: datetime | None = None
    ) -> dict[str, int]:
        """Get statistics by decision type for completed tasks."""
        query = select(
            DeclutterTask.decision, func.count(DeclutterTask.id)
        ).where(DeclutterTask.status == "done").group_by(DeclutterTask.decision)

        if since:
            query = query.where(DeclutterTask.updated_at >= since)

        result = await self.db.execute(query)
        return {row[0]: row[1] for row in result.all()}
