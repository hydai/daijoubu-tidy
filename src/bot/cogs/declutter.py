import logging
from typing import Literal
from uuid import UUID

import discord
from discord import app_commands
from discord.ext import commands

from src.core.database import get_db
from src.services.ai import AIService
from src.services.declutter import DeclutterTaskService

logger = logging.getLogger(__name__)

# 數字表情符號對應
NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


class DeclutterCog(commands.Cog):
    """斷捨離分析指令"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ai_service = AIService()
        # 儲存訊息 ID 與任務 ID 的對應關係
        # {message_id: [task_id1, task_id2, ...]}
        self.task_list_mapping: dict[int, list[UUID]] = {}

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

        items = result.get("items", [])
        if not items:
            await interaction.followup.send(
                "❌ 無法識別照片中的物品，請重新拍攝",
                ephemeral=True,
            )
            return

        decision_emoji = {
            "keep": "🟢 保留",
            "consider": "🟡 考慮",
            "discard": "🔴 捨棄",
        }

        # 為每個物品建立任務
        created_tasks = []
        async with get_db() as db:
            service = DeclutterTaskService(db)
            for item in items:
                item_name = item.get("name", "未知物品")
                decision = item.get("decision", "consider")
                reason = item.get("reason", "")
                action = item.get("action", "")

                # 組合分析內容
                analysis = f"**建議**：{decision_emoji.get(decision, '❓')}\n\n"
                analysis += f"**理由**：{reason}\n\n"
                analysis += f"**行動建議**：{action}"

                task = await service.create_task(
                    item_name=item_name,
                    analysis=analysis,
                    decision=decision,
                    image_url=image.url,
                    source_channel=interaction.channel.name
                    if interaction.channel
                    else None,
                    source_message_id=str(interaction.id),
                )
                created_tasks.append(
                    {
                        "task": task,
                        "item": item,
                    }
                )

        # 建立回應 Embed
        embed = discord.Embed(
            title=f"🧹 斷捨離分析結果（共 {len(created_tasks)} 個物品）",
            description="已為照片中的每個物品建立獨立任務",
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=image.url)

        for i, task_info in enumerate(created_tasks[:10]):  # 最多顯示 10 個
            task = task_info["task"]
            item = task_info["item"]
            task_id = str(task.id)[:8]
            decision = item.get("decision", "consider")
            reason = item.get("reason", "")

            embed.add_field(
                name=f"{NUMBER_EMOJIS[i]} {decision_emoji.get(decision, '❓')} {item.get('name', '未知')}",
                value=f"`{task_id}` - {reason[:60]}{'...' if len(reason) > 60 else ''}",
                inline=False,
            )

        embed.set_footer(text="使用 /tasks 查看任務清單並點擊表情快速標記完成")

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
        # 限制最多顯示 10 個（因為只有 10 個數字表情）
        limit = min(limit, 10)

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
            description=f"待處理: {stats['pending']} | 已完成: {stats['done']} | 已略過: {stats['dismissed']}\n\n點擊數字表情可快速切換完成狀態",
            color=discord.Color.blue(),
        )

        task_ids: list[UUID] = []
        for i, task in enumerate(tasks):
            task_ids.append(task.id)
            task_id_short = str(task.id)[:8]
            decision_icon = decision_emoji.get(task.decision, "⚪")
            status_icon = status_emoji.get(task.status, "❓")
            number_icon = NUMBER_EMOJIS[i]

            # 截取簡短分析
            short_analysis = (
                task.analysis[:80] + "..." if len(task.analysis) > 80 else task.analysis
            )

            embed.add_field(
                name=f"{number_icon} {status_icon} {decision_icon} {task.item_name}",
                value=f"`{task_id_short}` - {short_analysis}",
                inline=False,
            )

        embed.set_footer(text="點擊數字表情切換完成狀態 | /task-view <編號> 查看詳情")

        # 發送訊息
        message = await interaction.followup.send(embed=embed)

        # 儲存訊息與任務的對應關係
        self.task_list_mapping[message.id] = task_ids

        # 添加數字表情符號
        for i in range(len(tasks)):
            try:
                await message.add_reaction(NUMBER_EMOJIS[i])
            except discord.errors.Forbidden:
                logger.warning("無法添加表情符號，可能缺少權限")
                break

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        """處理表情符號添加事件"""
        # 忽略 Bot 自己的反應
        if payload.user_id == self.bot.user.id:
            return

        await self._handle_reaction(payload, is_adding=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        """處理表情符號移除事件"""
        # 忽略 Bot 自己的反應
        if payload.user_id == self.bot.user.id:
            return

        await self._handle_reaction(payload, is_adding=False)

    async def _handle_reaction(
        self, payload: discord.RawReactionActionEvent, is_adding: bool
    ) -> None:
        """處理表情符號反應"""
        message_id = payload.message_id
        emoji = str(payload.emoji)

        # 檢查是否為我們追蹤的訊息
        if message_id not in self.task_list_mapping:
            return

        # 檢查是否為數字表情
        if emoji not in NUMBER_EMOJIS:
            return

        # 取得對應的任務索引
        task_index = NUMBER_EMOJIS.index(emoji)
        task_ids = self.task_list_mapping[message_id]

        # 檢查索引是否有效
        if task_index >= len(task_ids):
            return

        task_id = task_ids[task_index]

        # 更新任務狀態
        async with get_db() as db:
            service = DeclutterTaskService(db)
            task = await service.get_task_by_id(task_id)

            if task:
                # 根據是添加還是移除反應來切換狀態
                # 添加反應 = 標記為完成，移除反應 = 標記為待處理
                new_status = "done" if is_adding else "pending"
                task.status = new_status
                item_name = task.item_name

        # 發送通知訊息
        try:
            channel = self.bot.get_channel(payload.channel_id)
            if channel:
                if is_adding:
                    await channel.send(
                        f"✅ **{item_name}** 已標記為完成！",
                        delete_after=5,
                    )
                else:
                    await channel.send(
                        f"⏳ **{item_name}** 已恢復為待處理",
                        delete_after=5,
                    )
        except Exception as e:
            logger.error(f"發送通知失敗: {e}")

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
            f"✅ 已將 **{task.item_name}** 標記為完成！"
            + (f"\n📝 記錄：{note}" if note else ""),
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
            f"⏭️ 已略過 **{task.item_name}**"
            + (f"\n📝 原因：{reason}" if reason else ""),
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
                "`/tasks` - 查看任務清單（可點擊數字表情切換狀態）\n"
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
