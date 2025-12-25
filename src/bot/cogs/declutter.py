import logging

import discord
from discord import app_commands
from discord.ext import commands

from src.services.ai import AIService

logger = logging.getLogger(__name__)


class DeclutterCog(commands.Cog):
    """斷捨離分析指令"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ai_service = AIService()

    @app_commands.command(name="declutter", description="上傳物品照片，獲得斷捨離建議")
    @app_commands.describe(image="要分析的物品照片")
    async def declutter(
        self, interaction: discord.Interaction, image: discord.Attachment
    ) -> None:
        """分析物品照片並提供斷捨離建議"""
        # 檢查是否為圖片
        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.response.send_message(
                "❌ 請上傳圖片檔案（JPG、PNG 等）",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        # 分析圖片
        result = await self.ai_service.analyze_image_for_declutter(image.url)

        if "error" in result:
            await interaction.followup.send(
                f"❌ {result['error']}",
                ephemeral=True,
            )
            return

        # 建立回應 Embed
        embed = discord.Embed(
            title="🧹 斷捨離分析結果",
            description=result["analysis"],
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=image.url)
        embed.set_footer(text="斷捨離：斷絕、捨棄、脫離")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="declutter-help", description="了解如何使用斷捨離功能")
    async def declutter_help(self, interaction: discord.Interaction) -> None:
        """顯示斷捨離功能說明"""
        embed = discord.Embed(
            title="🧹 斷捨離功能說明",
            description="上傳物品照片，AI 會幫你分析是否該保留或捨棄",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="📸 如何使用",
            value="輸入 `/declutter` 並上傳一張物品照片",
            inline=False,
        )

        embed.add_field(
            name="🎯 斷捨離三原則",
            value=(
                "**斷** - 斷絕不需要的東西進入生活\n"
                "**捨** - 捨棄堆放在家裡沒用的東西\n"
                "**離** - 脫離對物品的執著"
            ),
            inline=False,
        )

        embed.add_field(
            name="📊 評估標準",
            value=(
                "• 實用性：這個物品有實際用途嗎？\n"
                "• 使用頻率：最近一年內用過嗎？\n"
                "• 情感價值：有重要的紀念意義嗎？\n"
                "• 替代性：可以用其他東西替代嗎？\n"
                "• 狀態：物品的狀況如何？"
            ),
            inline=False,
        )

        embed.add_field(
            name="💡 建議結果",
            value=(
                "🟢 **保留** - 這個物品值得留下\n"
                "🟡 **考慮** - 需要再想想\n"
                "🔴 **捨棄** - 建議處理掉"
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DeclutterCog(bot))
