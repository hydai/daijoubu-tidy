import logging

import discord
from discord import app_commands
from discord.ext import commands

from src.core.database import get_db
from src.services.search import SearchService

logger = logging.getLogger(__name__)


class SearchCog(commands.Cog):
    """搜尋資訊的指令"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="search", description="語意搜尋（用自然語言描述你要找什麼）")
    @app_commands.describe(
        query="你想找什麼？",
        limit="最多顯示幾筆結果（預設：5）",
    )
    async def search(
        self, interaction: discord.Interaction, query: str, limit: int = 5
    ) -> None:
        """使用語意相似度搜尋項目"""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = SearchService(db)
            results = await service.semantic_search(query, limit=limit)

        if not results:
            await interaction.followup.send(
                f"🔍 找不到與「{query}」相關的內容", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🔍 搜尋結果：{query}",
            description=f"找到 {len(results)} 筆相關資料",
            color=discord.Color.purple(),
        )

        for item, score in results:
            content_preview = (
                item.content[:100] + "..." if len(item.content) > 100 else item.content
            )
            embed.add_field(
                name=f"{str(item.id)[:8]}（相似度：{score:.0%}）",
                value=content_preview,
                inline=False,
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="find", description="關鍵字搜尋")
    @app_commands.describe(
        keyword="要搜尋的關鍵字",
        limit="最多顯示幾筆結果（預設：10）",
    )
    async def find(
        self, interaction: discord.Interaction, keyword: str, limit: int = 10
    ) -> None:
        """使用關鍵字搜尋項目"""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = SearchService(db)
            results = await service.keyword_search(keyword, limit=limit)

        if not results:
            await interaction.followup.send(
                f"🔍 找不到包含「{keyword}」的內容", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🔎 關鍵字搜尋：{keyword}",
            description=f"找到 {len(results)} 筆資料",
            color=discord.Color.teal(),
        )

        type_names = {"text": "文字", "url": "網址", "image": "圖片"}
        for item in results:
            content_preview = (
                item.content[:100] + "..." if len(item.content) > 100 else item.content
            )
            type_name = type_names.get(item.content_type, item.content_type)
            embed.add_field(
                name=f"{str(item.id)[:8]} - {type_name}",
                value=content_preview,
                inline=False,
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="categories", description="列出所有分類")
    async def categories(self, interaction: discord.Interaction) -> None:
        """列出所有分類"""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = SearchService(db)
            categories = await service.list_categories()

        if not categories:
            await interaction.followup.send("📂 目前沒有任何分類", ephemeral=True)
            return

        embed = discord.Embed(
            title="📂 分類列表",
            description=f"共 {len(categories)} 個分類",
            color=discord.Color.gold(),
        )

        category_list = "\n".join(
            [f"• {cat.name}（{cat.description or '無說明'}）" for cat in categories]
        )
        embed.add_field(name="可用分類", value=category_list, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="tags", description="列出所有標籤")
    async def tags(self, interaction: discord.Interaction) -> None:
        """列出所有標籤"""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = SearchService(db)
            tags = await service.list_tags()

        if not tags:
            await interaction.followup.send("🏷️ 目前沒有任何標籤", ephemeral=True)
            return

        embed = discord.Embed(
            title="🏷️ 標籤列表",
            description=f"共 {len(tags)} 個標籤",
            color=discord.Color.orange(),
        )

        tag_list = ", ".join([tag.name for tag in tags])
        embed.add_field(name="可用標籤", value=tag_list, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SearchCog(bot))
