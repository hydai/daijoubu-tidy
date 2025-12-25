import logging

import discord
from discord import app_commands
from discord.ext import commands

from src.core.database import get_db
from src.services.search import SearchService

logger = logging.getLogger(__name__)


class SearchCog(commands.Cog):
    """Commands for searching saved information."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="search", description="Semantic search for items")
    @app_commands.describe(
        query="What are you looking for?",
        limit="Maximum number of results (default: 5)",
    )
    async def search(
        self, interaction: discord.Interaction, query: str, limit: int = 5
    ) -> None:
        """Search for items using semantic similarity."""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = SearchService(db)
            results = await service.semantic_search(query, limit=limit)

        if not results:
            await interaction.followup.send(
                f"No results found for: {query}", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"Search Results: {query}",
            description=f"Found {len(results)} item(s)",
            color=discord.Color.purple(),
        )

        for item, score in results:
            content_preview = (
                item.content[:100] + "..." if len(item.content) > 100 else item.content
            )
            embed.add_field(
                name=f"{str(item.id)[:8]} (similarity: {score:.2f})",
                value=content_preview,
                inline=False,
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="find", description="Keyword search for items")
    @app_commands.describe(
        keyword="Keyword to search for",
        limit="Maximum number of results (default: 10)",
    )
    async def find(
        self, interaction: discord.Interaction, keyword: str, limit: int = 10
    ) -> None:
        """Search for items using keyword matching."""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = SearchService(db)
            results = await service.keyword_search(keyword, limit=limit)

        if not results:
            await interaction.followup.send(
                f"No results found for: {keyword}", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"Keyword Results: {keyword}",
            description=f"Found {len(results)} item(s)",
            color=discord.Color.teal(),
        )

        for item in results:
            content_preview = (
                item.content[:100] + "..." if len(item.content) > 100 else item.content
            )
            embed.add_field(
                name=f"{str(item.id)[:8]} - {item.content_type}",
                value=content_preview,
                inline=False,
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="categories", description="List all categories")
    async def categories(self, interaction: discord.Interaction) -> None:
        """List all available categories."""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = SearchService(db)
            categories = await service.list_categories()

        if not categories:
            await interaction.followup.send("No categories found.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Categories",
            description=f"Total: {len(categories)} categories",
            color=discord.Color.gold(),
        )

        category_list = "\n".join(
            [f"- {cat.name} ({cat.description or 'No description'})" for cat in categories]
        )
        embed.add_field(name="Available Categories", value=category_list, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="tags", description="List all tags")
    async def tags(self, interaction: discord.Interaction) -> None:
        """List all available tags."""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = SearchService(db)
            tags = await service.list_tags()

        if not tags:
            await interaction.followup.send("No tags found.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Tags",
            description=f"Total: {len(tags)} tags",
            color=discord.Color.orange(),
        )

        tag_list = ", ".join([tag.name for tag in tags])
        embed.add_field(name="Available Tags", value=tag_list, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SearchCog(bot))
