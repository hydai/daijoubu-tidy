import logging

import discord
from discord import app_commands
from discord.ext import commands

from src.core.database import get_db
from src.services.items import ItemService

logger = logging.getLogger(__name__)


class CollectCog(commands.Cog):
    """收集與儲存資訊的指令"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="save", description="儲存文字資訊")
    @app_commands.describe(content="要儲存的內容")
    async def save(self, interaction: discord.Interaction, content: str) -> None:
        """儲存文字內容到資料庫"""
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
            title="✅ 已儲存",
            description="內容已成功儲存！",
            color=discord.Color.green(),
        )
        embed.add_field(name="ID", value=str(item.id)[:8], inline=True)
        embed.add_field(name="類型", value="文字", inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="save-url", description="儲存網址並自動擷取標題與摘要")
    @app_commands.describe(url="要儲存的網址")
    async def save_url(self, interaction: discord.Interaction, url: str) -> None:
        """儲存網址並擷取元資料"""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = ItemService(db)
            item = await service.create_item_from_url(
                url=url,
                source_channel=interaction.channel.name if interaction.channel else None,
                source_message_id=str(interaction.id),
            )

        embed = discord.Embed(
            title="🔗 網址已儲存",
            description=item.url_title or url,
            color=discord.Color.green(),
            url=url,
        )
        embed.add_field(name="ID", value=str(item.id)[:8], inline=True)
        if item.url_description:
            embed.add_field(name="摘要", value=item.url_description[:100], inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="tag", description="為項目加上標籤")
    @app_commands.describe(
        item_id="項目 ID（前 8 個字元）",
        tags="標籤（以逗號分隔）",
    )
    async def tag(
        self, interaction: discord.Interaction, item_id: str, tags: str
    ) -> None:
        """為現有項目加上標籤"""
        await interaction.response.defer(ephemeral=True)

        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        async with get_db() as db:
            service = ItemService(db)
            item = await service.add_tags(item_id, tag_list)

            if not item:
                await interaction.followup.send(
                    f"❌ 找不到 ID 開頭為 '{item_id}' 的項目",
                    ephemeral=True,
                )
                return

        embed = discord.Embed(
            title="🏷️ 標籤已新增",
            description=f"已為項目加上 {len(tag_list)} 個標籤",
            color=discord.Color.blue(),
        )
        embed.add_field(name="標籤", value=", ".join(tag_list), inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="list", description="列出已儲存的項目")
    @app_commands.describe(
        category="依分類篩選（可選）",
        limit="顯示數量（預設：10）",
    )
    async def list_items(
        self,
        interaction: discord.Interaction,
        category: str | None = None,
        limit: int = 10,
    ) -> None:
        """列出已儲存的項目"""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = ItemService(db)
            items = await service.list_items(category=category, limit=limit)

        if not items:
            await interaction.followup.send("📭 目前沒有任何項目", ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 已儲存的項目",
            description=f"共 {len(items)} 筆資料",
            color=discord.Color.blue(),
        )

        type_names = {"text": "文字", "url": "網址", "image": "圖片"}
        for item in items:
            content_preview = (
                item.content[:50] + "..." if len(item.content) > 50 else item.content
            )
            type_name = type_names.get(item.content_type, item.content_type)
            embed.add_field(
                name=f"{str(item.id)[:8]} - {type_name}",
                value=content_preview,
                inline=False,
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="delete", description="刪除項目")
    @app_commands.describe(item_id="項目 ID（前 8 個字元）")
    async def delete(self, interaction: discord.Interaction, item_id: str) -> None:
        """刪除指定項目"""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = ItemService(db)
            deleted = await service.delete_item(item_id)

            if not deleted:
                await interaction.followup.send(
                    f"❌ 找不到 ID 開頭為 '{item_id}' 的項目",
                    ephemeral=True,
                )
                return

        embed = discord.Embed(
            title="🗑️ 已刪除",
            description=f"項目 {item_id} 已被刪除",
            color=discord.Color.red(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CollectCog(bot))
