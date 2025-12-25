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
    """摘要與統計的指令"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="summary", description="產生資訊摘要報告")
    @app_commands.describe(period="摘要的時間範圍")
    @app_commands.choices(
        period=[
            app_commands.Choice(name="今天", value="daily"),
            app_commands.Choice(name="本週", value="weekly"),
            app_commands.Choice(name="本月", value="monthly"),
        ]
    )
    async def summary(
        self, interaction: discord.Interaction, period: str = "daily"
    ) -> None:
        """產生指定時間範圍的資訊摘要"""
        await interaction.response.defer(ephemeral=True)

        # 計算時間範圍
        now = datetime.now(timezone.utc)
        if period == "daily":
            start_date = now - timedelta(days=1)
            period_name = "今天"
        elif period == "weekly":
            start_date = now - timedelta(weeks=1)
            period_name = "本週"
        else:
            start_date = now - timedelta(days=30)
            period_name = "本月"

        async with get_db() as db:
            item_service = ItemService(db)
            items = await item_service.get_items_since(start_date)

            if not items:
                await interaction.followup.send(
                    f"📭 {period_name}沒有儲存任何項目", ephemeral=True
                )
                return

            # 產生 AI 摘要
            ai_service = AIService()
            summary_text = await ai_service.generate_summary(items)

        embed = discord.Embed(
            title=f"📊 {period_name}的摘要",
            description=summary_text,
            color=discord.Color.blurple(),
            timestamp=now,
        )
        embed.add_field(name="項目數量", value=str(len(items)), inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="stats", description="查看使用統計")
    async def stats(self, interaction: discord.Interaction) -> None:
        """顯示使用統計資訊"""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = ItemService(db)
            stats = await service.get_stats()

        embed = discord.Embed(
            title="📈 使用統計",
            description="你的資訊收集統計數據",
            color=discord.Color.dark_blue(),
        )
        embed.add_field(name="總項目數", value=str(stats["total_items"]), inline=True)
        embed.add_field(name="分類數", value=str(stats["total_categories"]), inline=True)
        embed.add_field(name="標籤數", value=str(stats["total_tags"]), inline=True)

        if stats["items_by_type"]:
            type_names = {"text": "文字", "url": "網址", "image": "圖片"}
            type_breakdown = "\n".join(
                [f"• {type_names.get(t, t)}：{c} 筆" for t, c in stats["items_by_type"].items()]
            )
            embed.add_field(name="依類型統計", value=type_breakdown, inline=False)

        if stats["recent_items"]:
            embed.add_field(
                name="近 7 天新增", value=f"{stats['recent_items']} 筆", inline=True
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="export", description="匯出所有資料")
    @app_commands.describe(format="匯出格式")
    @app_commands.choices(
        format=[
            app_commands.Choice(name="JSON", value="json"),
            app_commands.Choice(name="CSV", value="csv"),
        ]
    )
    async def export(
        self, interaction: discord.Interaction, format: str = "json"
    ) -> None:
        """匯出所有已儲存的資料"""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = ItemService(db)
            data = await service.export_data(format=format)

        if not data:
            await interaction.followup.send("📭 沒有資料可匯出", ephemeral=True)
            return

        # 建立檔案
        filename = f"daijoubu_export.{format}"
        file = discord.File(
            fp=data,
            filename=filename,
        )

        await interaction.followup.send(
            content=f"📦 這是你的 {format.upper()} 格式匯出檔案：",
            file=file,
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SummaryCog(bot))
