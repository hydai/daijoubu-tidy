import io
import json
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Category, Item, Tag
from src.services.ai import AIService


class ItemService:
    """Service for managing items."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.ai_service = AIService()

    async def create_item(
        self,
        content: str,
        content_type: str = "text",
        url: str | None = None,
        url_title: str | None = None,
        url_description: str | None = None,
        source_channel: str | None = None,
        source_message_id: str | None = None,
    ) -> Item:
        """Create a new item."""
        # Generate embedding
        embedding = await self.ai_service.generate_embedding(content)

        item = Item(
            content=content,
            content_type=content_type,
            url=url,
            url_title=url_title,
            url_description=url_description,
            source_channel=source_channel,
            source_message_id=source_message_id,
            embedding=embedding,
        )

        self.db.add(item)
        await self.db.flush()

        # Auto-categorize
        await self._auto_categorize(item)

        return item

    async def create_item_from_url(
        self,
        url: str,
        source_channel: str | None = None,
        source_message_id: str | None = None,
    ) -> Item:
        """Create an item from a URL, fetching metadata."""
        url_title, url_description = await self._fetch_url_metadata(url)

        content = f"{url_title or url}\n{url_description or ''}"

        return await self.create_item(
            content=content,
            content_type="url",
            url=url,
            url_title=url_title,
            url_description=url_description,
            source_channel=source_channel,
            source_message_id=source_message_id,
        )

    async def _fetch_url_metadata(self, url: str) -> tuple[str | None, str | None]:
        """Fetch title and description from a URL."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                html = response.text

                # Simple title extraction
                title = None
                if "<title>" in html:
                    start = html.find("<title>") + 7
                    end = html.find("</title>")
                    if end > start:
                        title = html[start:end].strip()

                # Simple meta description extraction
                description = None
                if 'name="description"' in html or 'name="Description"' in html:
                    for pattern in ['name="description" content="', 'name="Description" content="']:
                        if pattern in html:
                            start = html.find(pattern) + len(pattern)
                            end = html.find('"', start)
                            if end > start:
                                description = html[start:end].strip()
                                break

                return title, description
        except Exception:
            return None, None

    async def _auto_categorize(self, item: Item) -> None:
        """Automatically categorize an item using AI."""
        category_name = await self.ai_service.classify_content(item.content)

        if category_name:
            # Get or create category
            result = await self.db.execute(
                select(Category).where(Category.name == category_name)
            )
            category = result.scalar_one_or_none()

            if not category:
                category = Category(name=category_name)
                self.db.add(category)
                await self.db.flush()

            item.categories.append(category)

    async def add_tags(self, item_id_prefix: str, tag_names: list[str]) -> Item | None:
        """Add tags to an item."""
        # Find item by ID prefix
        result = await self.db.execute(
            select(Item)
            .where(func.cast(Item.id, String).like(f"{item_id_prefix}%"))
            .options(selectinload(Item.tags))
        )
        item = result.scalar_one_or_none()

        if not item:
            return None

        for tag_name in tag_names:
            # Get or create tag
            tag_result = await self.db.execute(
                select(Tag).where(Tag.name == tag_name)
            )
            tag = tag_result.scalar_one_or_none()

            if not tag:
                tag = Tag(name=tag_name)
                self.db.add(tag)
                await self.db.flush()

            if tag not in item.tags:
                item.tags.append(tag)

        return item

    async def list_items(
        self, category: str | None = None, limit: int = 10
    ) -> list[Item]:
        """List items with optional filtering."""
        query = select(Item).order_by(Item.created_at.desc()).limit(limit)

        if category:
            query = query.join(Item.categories).where(Category.name == category)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_items_since(self, since: datetime) -> list[Item]:
        """Get items created since a specific time."""
        result = await self.db.execute(
            select(Item)
            .where(Item.created_at >= since)
            .order_by(Item.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_item(self, item_id_prefix: str) -> bool:
        """Delete an item by ID prefix."""
        result = await self.db.execute(
            select(Item).where(func.cast(Item.id, String).like(f"{item_id_prefix}%"))
        )
        item = result.scalar_one_or_none()

        if not item:
            return False

        await self.db.delete(item)
        return True

    async def get_stats(self) -> dict[str, Any]:
        """Get usage statistics."""
        from datetime import timedelta, timezone

        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        # Total items
        total_result = await self.db.execute(select(func.count(Item.id)))
        total_items = total_result.scalar() or 0

        # Total categories
        cat_result = await self.db.execute(select(func.count(Category.id)))
        total_categories = cat_result.scalar() or 0

        # Total tags
        tag_result = await self.db.execute(select(func.count(Tag.id)))
        total_tags = tag_result.scalar() or 0

        # Items by type
        type_result = await self.db.execute(
            select(Item.content_type, func.count(Item.id)).group_by(Item.content_type)
        )
        items_by_type = {row[0]: row[1] for row in type_result.all()}

        # Recent items count
        recent_result = await self.db.execute(
            select(func.count(Item.id)).where(Item.created_at >= week_ago)
        )
        recent_items = recent_result.scalar() or 0

        return {
            "total_items": total_items,
            "total_categories": total_categories,
            "total_tags": total_tags,
            "items_by_type": items_by_type,
            "recent_items": recent_items,
        }

    async def export_data(self, format: str = "json") -> io.BytesIO | None:
        """Export all items in the specified format."""
        result = await self.db.execute(
            select(Item)
            .options(selectinload(Item.categories), selectinload(Item.tags))
            .order_by(Item.created_at)
        )
        items = result.scalars().all()

        if not items:
            return None

        if format == "json":
            data = [
                {
                    "id": str(item.id),
                    "content": item.content,
                    "content_type": item.content_type,
                    "url": item.url,
                    "url_title": item.url_title,
                    "categories": [c.name for c in item.categories],
                    "tags": [t.name for t in item.tags],
                    "created_at": item.created_at.isoformat(),
                }
                for item in items
            ]
            content = json.dumps(data, ensure_ascii=False, indent=2)
            return io.BytesIO(content.encode("utf-8"))

        elif format == "csv":
            import csv

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                ["id", "content", "content_type", "url", "categories", "tags", "created_at"]
            )

            for item in items:
                writer.writerow(
                    [
                        str(item.id),
                        item.content,
                        item.content_type,
                        item.url or "",
                        ",".join([c.name for c in item.categories]),
                        ",".join([t.name for t in item.tags]),
                        item.created_at.isoformat(),
                    ]
                )

            return io.BytesIO(output.getvalue().encode("utf-8"))

        return None
