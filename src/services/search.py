from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Category, Item, Tag
from src.services.ai import AIService


class SearchService:
    """Service for searching items."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.ai_service = AIService()

    async def semantic_search(
        self, query: str, limit: int = 5
    ) -> list[tuple[Item, float]]:
        """Search items using semantic similarity."""
        # Generate query embedding
        query_embedding = await self.ai_service.generate_embedding(query)

        if not query_embedding:
            return []

        # Perform vector similarity search
        result = await self.db.execute(
            select(
                Item,
                Item.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .where(Item.embedding.isnot(None))
            .order_by("distance")
            .limit(limit)
        )

        items_with_scores = []
        for row in result.all():
            item = row[0]
            distance = row[1]
            # Convert distance to similarity (1 - distance for cosine distance)
            similarity = 1 - distance if distance else 0
            items_with_scores.append((item, similarity))

        return items_with_scores

    async def keyword_search(self, keyword: str, limit: int = 10) -> list[Item]:
        """Search items using keyword matching."""
        search_pattern = f"%{keyword}%"

        result = await self.db.execute(
            select(Item)
            .where(Item.content.ilike(search_pattern))
            .order_by(Item.created_at.desc())
            .limit(limit)
        )

        return list(result.scalars().all())

    async def list_categories(self) -> list[Category]:
        """List all categories."""
        result = await self.db.execute(
            select(Category).order_by(Category.name)
        )
        return list(result.scalars().all())

    async def list_tags(self) -> list[Tag]:
        """List all tags."""
        result = await self.db.execute(select(Tag).order_by(Tag.name))
        return list(result.scalars().all())
