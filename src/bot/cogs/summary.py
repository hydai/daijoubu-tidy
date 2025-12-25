import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from src.core.database import get_db
from src.services.items import ItemService
from src.services.ai import AIService

logger = logging.getLogger(__name__)


class SummaryCog(commands.Cog):
    """Commands for summaries and statistics."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="summary", description="Get a summary of your items")
    @app_commands.describe(period="Time period for summary")
    @app_commands.choices(
        period=[
            app_commands.Choice(name="Today", value="daily"),
            app_commands.Choice(name="This Week", value="weekly"),
            app_commands.Choice(name="This Month", value="monthly"),
        ]
    )
    async def summary(
        self, interaction: discord.Interaction, period: str = "daily"
    ) -> None:
        """Generate a summary of saved items for a time period."""
        await interaction.response.defer(ephemeral=True)

        # Calculate date range
        now = datetime.now(timezone.utc)
        if period == "daily":
            start_date = now - timedelta(days=1)
            period_name = "Today"
        elif period == "weekly":
            start_date = now - timedelta(weeks=1)
            period_name = "This Week"
        else:
            start_date = now - timedelta(days=30)
            period_name = "This Month"

        async with get_db() as db:
            item_service = ItemService(db)
            items = await item_service.get_items_since(start_date)

            if not items:
                await interaction.followup.send(
                    f"No items saved in {period_name.lower()}.", ephemeral=True
                )
                return

            # Generate AI summary
            ai_service = AIService()
            summary_text = await ai_service.generate_summary(items)

        embed = discord.Embed(
            title=f"Summary - {period_name}",
            description=summary_text,
            color=discord.Color.blurple(),
            timestamp=now,
        )
        embed.add_field(name="Items Count", value=str(len(items)), inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="stats", description="View usage statistics")
    async def stats(self, interaction: discord.Interaction) -> None:
        """Show usage statistics."""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = ItemService(db)
            stats = await service.get_stats()

        embed = discord.Embed(
            title="Statistics",
            description="Your information collection stats",
            color=discord.Color.dark_blue(),
        )
        embed.add_field(name="Total Items", value=str(stats["total_items"]), inline=True)
        embed.add_field(name="Categories", value=str(stats["total_categories"]), inline=True)
        embed.add_field(name="Tags", value=str(stats["total_tags"]), inline=True)

        if stats["items_by_type"]:
            type_breakdown = "\n".join(
                [f"- {t}: {c}" for t, c in stats["items_by_type"].items()]
            )
            embed.add_field(name="By Type", value=type_breakdown, inline=False)

        if stats["recent_items"]:
            embed.add_field(
                name="Items (Last 7 days)", value=str(stats["recent_items"]), inline=True
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="export", description="Export your data")
    @app_commands.describe(format="Export format")
    @app_commands.choices(
        format=[
            app_commands.Choice(name="JSON", value="json"),
            app_commands.Choice(name="CSV", value="csv"),
        ]
    )
    async def export(
        self, interaction: discord.Interaction, format: str = "json"
    ) -> None:
        """Export all saved data."""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = ItemService(db)
            data = await service.export_data(format=format)

        if not data:
            await interaction.followup.send("No data to export.", ephemeral=True)
            return

        # Create file
        filename = f"daijoubu_export.{format}"
        file = discord.File(
            fp=data,
            filename=filename,
        )

        await interaction.followup.send(
            content=f"Here's your data export in {format.upper()} format:",
            file=file,
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SummaryCog(bot))
