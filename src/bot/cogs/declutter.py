import logging
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from src.core.database import get_db
from src.services.ai import AIService
from src.services.declutter import (
    DeclutterTaskService,
    parse_decision_from_analysis,
    parse_item_name_from_analysis,
)

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
        """分析物品照片並提供斷捨離建議，自動建立任務追蹤"""
        # 檢查是否為圖片
        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.response.send_message(
                "❌ 請上傳圖片檔案（JPG、PNG 等）",
                ephemeral=True,
            )
            return

        await interaction.response.defer()  # 改為公開訊息

        # 分析圖片
        result = await self.ai_service.analyze_image_for_declutter(image.url)

        if "error" in result:
            await interaction.followup.send(
                f"❌ {result['error']}",
                ephemeral=True,
            )
            return

        analysis = result["analysis"]
        decision = parse_decision_from_analysis(analysis)
        item_name = parse_item_name_from_analysis(analysis)

        # 儲存到資料庫
        async with get_db() as db:
            service = DeclutterTaskService(db)
            task = await service.create_task(
                item_name=item_name,
                analysis=analysis,
                decision=decision,
                image_url=image.url,
                source_channel=interaction.channel.name if interaction.channel else None,
                source_message_id=str(interaction.id),
            )
            task_id = str(task.id)[:8]

        # 決定顏色
        color_map = {
            "keep": discord.Color.green(),
            "consider": discord.Color.gold(),
            "discard": discord.Color.red(),
        }

        # 建立回應 Embed
        embed = discord.Embed(
            title="🧹 斷捨離分析結果",
            description=analysis,
            color=color_map.get(decision, discord.Color.blue()),
        )
        embed.set_thumbnail(url=image.url)
        embed.add_field(
            name="📋 任務編號",
            value=f"`{task_id}`",
            inline=True,
        )
        embed.add_field(
            name="📊 狀態",
            value="⏳ 待處理",
            inline=True,
        )
        embed.set_footer(text="使用 /tasks 查看所有任務 | /task-done 標記完成")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="tasks", description="查看斷捨離任務清單")
    @app_commands.describe(
        status="篩選任務狀態",
        limit="顯示數量（預設 10）",
    )
    async def list_tasks(
        self,
        interaction: discord.Interaction,
        status: Literal["all", "pending", "done", "dismissed"] = "pending",
        limit: int = 10,
    ) -> None:
        """列出斷捨離任務"""
        await interaction.response.defer()

        async with get_db() as db:
            service = DeclutterTaskService(db)

            filter_status = None if status == "all" else status
            tasks = await service.list_tasks(status=filter_status, limit=limit)
            stats = await service.get_stats()

        if not tasks:
            await interaction.followup.send(
                f"📭 沒有{'待處理的' if status == 'pending' else ''}任務",
                ephemeral=True,
            )
            return

        # 狀態符號
        status_emoji = {
            "pending": "⏳",
            "done": "✅",
            "dismissed": "❌",
        }

        decision_emoji = {
            "keep": "🟢",
            "consider": "🟡",
            "discard": "🔴",
        }

        # 建立 Embed
        embed = discord.Embed(
            title="📋 斷捨離任務清單",
            description=f"待處理: {stats['pending']} | 已完成: {stats['done']} | 已略過: {stats['dismissed']}",
            color=discord.Color.blue(),
        )

        for task in tasks:
            task_id = str(task.id)[:8]
            decision_icon = decision_emoji.get(task.decision, "⚪")
            status_icon = status_emoji.get(task.status, "❓")

            # 截取簡短分析
            short_analysis = task.analysis[:100] + "..." if len(task.analysis) > 100 else task.analysis

            embed.add_field(
                name=f"{status_icon} {decision_icon} {task.item_name} (`{task_id}`)",
                value=short_analysis,
                inline=False,
            )

        embed.set_footer(text="使用 /task-done <編號> 標記完成 | /task-view <編號> 查看詳情")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="task-view", description="查看任務詳情")
    @app_commands.describe(task_id="任務編號（前 8 碼）")
    async def view_task(
        self,
        interaction: discord.Interaction,
        task_id: str,
    ) -> None:
        """查看任務詳細內容"""
        await interaction.response.defer()

        async with get_db() as db:
            service = DeclutterTaskService(db)
            task = await service.get_task_by_prefix(task_id)

        if not task:
            await interaction.followup.send(
                f"❌ 找不到任務 `{task_id}`",
                ephemeral=True,
            )
            return

        # 狀態符號
        status_emoji = {
            "pending": "⏳ 待處理",
            "done": "✅ 已完成",
            "dismissed": "❌ 已略過",
        }

        decision_emoji = {
            "keep": "🟢 保留",
            "consider": "🟡 考慮",
            "discard": "🔴 捨棄",
        }

        color_map = {
            "keep": discord.Color.green(),
            "consider": discord.Color.gold(),
            "discard": discord.Color.red(),
        }

        embed = discord.Embed(
            title=f"📋 {task.item_name}",
            description=task.analysis,
            color=color_map.get(task.decision, discord.Color.blue()),
        )

        if task.image_url:
            embed.set_thumbnail(url=task.image_url)

        embed.add_field(
            name="📊 建議",
            value=decision_emoji.get(task.decision, "❓"),
            inline=True,
        )
        embed.add_field(
            name="📌 狀態",
            value=status_emoji.get(task.status, "❓"),
            inline=True,
        )
        embed.add_field(
            name="🔢 編號",
            value=f"`{str(task.id)[:8]}`",
            inline=True,
        )

        if task.action_taken:
            embed.add_field(
                name="✍️ 處理記錄",
                value=task.action_taken,
                inline=False,
            )

        embed.add_field(
            name="📅 建立時間",
            value=task.created_at.strftime("%Y-%m-%d %H:%M"),
            inline=True,
        )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="task-done", description="標記任務為已完成")
    @app_commands.describe(
        task_id="任務編號（前 8 碼）",
        note="處理記錄（可選）",
    )
    async def mark_done(
        self,
        interaction: discord.Interaction,
        task_id: str,
        note: str | None = None,
    ) -> None:
        """標記任務為已完成"""
        async with get_db() as db:
            service = DeclutterTaskService(db)
            task = await service.update_task_status(
                task_id,
                status="done",
                action_taken=note,
            )

        if not task:
            await interaction.response.send_message(
                f"❌ 找不到任務 `{task_id}`",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ 已將 **{task.item_name}** 標記為完成！" +
            (f"\n📝 記錄：{note}" if note else ""),
        )

    @app_commands.command(name="task-dismiss", description="略過/忽略任務")
    @app_commands.describe(
        task_id="任務編號（前 8 碼）",
        reason="略過原因（可選）",
    )
    async def dismiss_task(
        self,
        interaction: discord.Interaction,
        task_id: str,
        reason: str | None = None,
    ) -> None:
        """略過任務"""
        async with get_db() as db:
            service = DeclutterTaskService(db)
            task = await service.update_task_status(
                task_id,
                status="dismissed",
                action_taken=reason,
            )

        if not task:
            await interaction.response.send_message(
                f"❌ 找不到任務 `{task_id}`",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"⏭️ 已略過 **{task.item_name}**" +
            (f"\n📝 原因：{reason}" if reason else ""),
        )

    @app_commands.command(name="task-delete", description="刪除任務")
    @app_commands.describe(task_id="任務編號（前 8 碼）")
    async def delete_task(
        self,
        interaction: discord.Interaction,
        task_id: str,
    ) -> None:
        """刪除任務"""
        async with get_db() as db:
            service = DeclutterTaskService(db)
            deleted = await service.delete_task(task_id)

        if not deleted:
            await interaction.response.send_message(
                f"❌ 找不到任務 `{task_id}`",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(f"🗑️ 已刪除任務 `{task_id}`")

    @app_commands.command(name="declutter-help", description="了解如何使用斷捨離功能")
    async def declutter_help(self, interaction: discord.Interaction) -> None:
        """顯示斷捨離功能說明"""
        embed = discord.Embed(
            title="🧹 斷捨離功能說明",
            description="上傳物品照片，AI 會幫你分析是否該保留或捨棄，並自動建立任務追蹤",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="📸 分析物品",
            value="`/declutter` + 上傳照片 → AI 分析 + 建立任務",
            inline=False,
        )

        embed.add_field(
            name="📋 管理任務",
            value=(
                "`/tasks` - 查看任務清單\n"
                "`/task-view <編號>` - 查看詳情\n"
                "`/task-done <編號>` - 標記完成\n"
                "`/task-dismiss <編號>` - 略過任務\n"
                "`/task-delete <編號>` - 刪除任務"
            ),
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
