import io
import json
import logging
from datetime import UTC, datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from src.core.database import get_db
from src.services.declutter import DeclutterTaskService

logger = logging.getLogger(__name__)


class SummaryCog(commands.Cog):
    """斷捨離統計與摘要指令"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="stats", description="查看斷捨離統計")
    async def stats(self, interaction: discord.Interaction) -> None:
        """顯示斷捨離進度統計"""
        await interaction.response.defer()

        async with get_db() as db:
            service = DeclutterTaskService(db)
            stats = await service.get_stats()
            recent_done = await service.get_recent_completed(days=7)
            recent_created = await service.get_recent_created(days=7)

        total = stats["total"]
        done = stats["done"]
        pending = stats["pending"]
        dismissed = stats["dismissed"]

        # 計算完成率
        completion_rate = (done / total * 100) if total > 0 else 0

        embed = discord.Embed(
            title="📊 斷捨離統計",
            description="你的斷捨離進度一覽",
            color=discord.Color.blue(),
        )

        # 總覽
        embed.add_field(
            name="📋 任務總覽",
            value=(
                f"總任務數：**{total}** 個\n"
                f"✅ 已完成：**{done}** 個\n"
                f"⏳ 待處理：**{pending}** 個\n"
                f"❌ 已略過：**{dismissed}** 個"
            ),
            inline=True,
        )

        # 完成率
        progress_bar = self._create_progress_bar(completion_rate)
        embed.add_field(
            name="🎯 完成率",
            value=f"{progress_bar}\n**{completion_rate:.1f}%**",
            inline=True,
        )

        # 近期活動
        embed.add_field(
            name="📅 近 7 天",
            value=(f"新增：**{recent_created}** 個\n完成：**{recent_done}** 個"),
            inline=True,
        )

        # 鼓勵訊息
        if completion_rate >= 80:
            message = "🎉 太棒了！你的斷捨離進度非常出色！"
        elif completion_rate >= 50:
            message = "💪 繼續加油！你已經完成一半以上了！"
        elif completion_rate >= 20:
            message = "🌱 好的開始！持續整理會越來越輕鬆！"
        else:
            message = "✨ 開始斷捨離之旅吧！每一步都是進步！"

        embed.set_footer(text=message)

        await interaction.followup.send(embed=embed)

    def _create_progress_bar(self, percentage: float, length: int = 10) -> str:
        """建立進度條"""
        filled = int(percentage / 100 * length)
        empty = length - filled
        return "█" * filled + "░" * empty

    @app_commands.command(name="summary", description="產生斷捨離成果報告")
    @app_commands.describe(period="報告的時間範圍")
    @app_commands.choices(
        period=[
            app_commands.Choice(name="本週", value="weekly"),
            app_commands.Choice(name="本月", value="monthly"),
            app_commands.Choice(name="全部", value="all"),
        ]
    )
    async def summary(
        self, interaction: discord.Interaction, period: str = "weekly"
    ) -> None:
        """產生斷捨離成果報告"""
        await interaction.response.defer()

        # 計算時間範圍
        now = datetime.now(UTC)
        if period == "weekly":
            start_date = now - timedelta(weeks=1)
            period_name = "本週"
        elif period == "monthly":
            start_date = now - timedelta(days=30)
            period_name = "本月"
        else:
            start_date = None
            period_name = "全部"

        async with get_db() as db:
            service = DeclutterTaskService(db)
            completed_tasks = await service.get_completed_tasks(since=start_date)
            stats = await service.get_decision_stats(since=start_date)

        if not completed_tasks:
            await interaction.followup.send(
                f"📭 {period_name}還沒有完成任何斷捨離任務\n使用 `/declutter` 開始分析物品！"
            )
            return

        embed = discord.Embed(
            title=f"🏆 {period_name}斷捨離成果",
            description=f"你{period_name}完成了 **{len(completed_tasks)}** 個斷捨離任務！",
            color=discord.Color.gold(),
        )

        # 決定統計
        embed.add_field(
            name="📊 處理結果分布",
            value=(
                f"🟢 保留：**{stats.get('keep', 0)}** 個\n"
                f"🟡 考慮後處理：**{stats.get('consider', 0)}** 個\n"
                f"🔴 成功捨棄：**{stats.get('discard', 0)}** 個"
            ),
            inline=False,
        )

        # 最近完成的物品
        recent_items = completed_tasks[:5]
        items_text = "\n".join([f"• {task.item_name}" for task in recent_items])
        if len(completed_tasks) > 5:
            items_text += f"\n... 還有 {len(completed_tasks) - 5} 個"

        embed.add_field(
            name="✅ 已完成的物品",
            value=items_text,
            inline=False,
        )

        # 鼓勵訊息
        discard_count = stats.get("discard", 0)
        if discard_count >= 10:
            footer = "🎊 太厲害了！你成功清理了很多物品！"
        elif discard_count >= 5:
            footer = "👏 做得好！持續斷捨離，生活會更輕鬆！"
        else:
            footer = "💫 每次整理都是進步，繼續加油！"

        embed.set_footer(text=footer)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="export", description="匯出斷捨離記錄")
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
        """匯出斷捨離任務記錄"""
        await interaction.response.defer(ephemeral=True)

        async with get_db() as db:
            service = DeclutterTaskService(db)
            tasks = await service.list_tasks(status=None, limit=1000)

        if not tasks:
            await interaction.followup.send("📭 沒有任何記錄可匯出", ephemeral=True)
            return

        if format == "json":
            data = [
                {
                    "id": str(task.id)[:8],
                    "item_name": task.item_name,
                    "decision": task.decision,
                    "status": task.status,
                    "analysis": task.analysis,
                    "action_taken": task.action_taken,
                    "created_at": task.created_at.isoformat(),
                }
                for task in tasks
            ]
            content = json.dumps(data, ensure_ascii=False, indent=2)
            file_data = io.BytesIO(content.encode("utf-8"))
            filename = "declutter_export.json"
        else:
            import csv

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["編號", "物品", "建議", "狀態", "處理記錄", "建立時間"])
            for task in tasks:
                writer.writerow(
                    [
                        str(task.id)[:8],
                        task.item_name,
                        task.decision,
                        task.status,
                        task.action_taken or "",
                        task.created_at.strftime("%Y-%m-%d %H:%M"),
                    ]
                )
            file_data = io.BytesIO(output.getvalue().encode("utf-8"))
            filename = "declutter_export.csv"

        file = discord.File(fp=file_data, filename=filename)
        await interaction.followup.send(
            content=f"📦 這是你的斷捨離記錄（{format.upper()} 格式）：",
            file=file,
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SummaryCog(bot))
