import logging

import discord
from discord import app_commands
from discord.ext import commands

from src.core.database import get_db
from src.models import Item, Tag
from src.services.items import ItemService

logger = logging.getLogger(__name__)


class CollectCog(commands.Cog):
    """Commands for collecting and saving information."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="save", description="Save text information")
    @app_commands.describe(content="The content to save")
    async def save(self, interaction: discord.Interaction, content: str) -> None:
        """Save text content to the database."""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = ItemService(db)
            item = await service.create_item(
                content=content,
                content_type="text",
                source_channel=interaction.channel.name if interaction.channel else None,
                source_message_id=str(interaction.id),
            )

        embed = discord.Embed(
            title="Saved",
            description=f"Content saved successfully!",
            color=discord.Color.green(),
        )
        embed.add_field(name="ID", value=str(item.id)[:8], inline=True)
        embed.add_field(name="Type", value=item.content_type, inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="save-url", description="Save a URL with metadata")
    @app_commands.describe(url="The URL to save")
    async def save_url(self, interaction: discord.Interaction, url: str) -> None:
        """Save a URL and fetch its metadata."""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = ItemService(db)
            item = await service.create_item_from_url(
                url=url,
                source_channel=interaction.channel.name if interaction.channel else None,
                source_message_id=str(interaction.id),
            )

        embed = discord.Embed(
            title="URL Saved",
            description=item.url_title or url,
            color=discord.Color.green(),
            url=url,
        )
        embed.add_field(name="ID", value=str(item.id)[:8], inline=True)
        if item.url_description:
            embed.add_field(name="Description", value=item.url_description[:100], inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="tag", description="Add tags to an item")
    @app_commands.describe(
        item_id="The item ID (first 8 characters)",
        tags="Comma-separated tags to add",
    )
    async def tag(
        self, interaction: discord.Interaction, item_id: str, tags: str
    ) -> None:
        """Add tags to an existing item."""
        await interaction.response.defer(ephemeral=True)

        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        async with get_db() as db:
            service = ItemService(db)
            item = await service.add_tags(item_id, tag_list)

            if not item:
                await interaction.followup.send(
                    f"Item with ID starting with '{item_id}' not found.",
                    ephemeral=True,
                )
                return

        embed = discord.Embed(
            title="Tags Added",
            description=f"Added {len(tag_list)} tag(s) to item",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Tags", value=", ".join(tag_list), inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="list", description="List saved items")
    @app_commands.describe(
        category="Filter by category (optional)",
        limit="Number of items to show (default: 10)",
    )
    async def list_items(
        self,
        interaction: discord.Interaction,
        category: str | None = None,
        limit: int = 10,
    ) -> None:
        """List saved items with optional filtering."""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = ItemService(db)
            items = await service.list_items(category=category, limit=limit)

        if not items:
            await interaction.followup.send("No items found.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Saved Items",
            description=f"Showing {len(items)} item(s)",
            color=discord.Color.blue(),
        )

        for item in items:
            content_preview = (
                item.content[:50] + "..." if len(item.content) > 50 else item.content
            )
            embed.add_field(
                name=f"{str(item.id)[:8]} - {item.content_type}",
                value=content_preview,
                inline=False,
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="delete", description="Delete an item")
    @app_commands.describe(item_id="The item ID (first 8 characters)")
    async def delete(self, interaction: discord.Interaction, item_id: str) -> None:
        """Delete an item by ID."""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = ItemService(db)
            deleted = await service.delete_item(item_id)

            if not deleted:
                await interaction.followup.send(
                    f"Item with ID starting with '{item_id}' not found.",
                    ephemeral=True,
                )
                return

        embed = discord.Embed(
            title="Item Deleted",
            description=f"Item {item_id} has been deleted.",
            color=discord.Color.red(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CollectCog(bot))
