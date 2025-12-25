import asyncio
import logging

import discord
from discord.ext import commands

from src.core.config import settings
from src.core.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DaijoubuBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            description="AI-powered personal information organizer",
        )

    async def setup_hook(self) -> None:
        """Called when the bot is starting up."""
        logger.info("Initializing database...")
        await init_db()

        # Load cogs
        await self.load_extension("src.bot.cogs.collect")
        await self.load_extension("src.bot.cogs.search")
        await self.load_extension("src.bot.cogs.summary")

        # Sync slash commands
        if settings.discord_guild_id:
            guild = discord.Object(id=int(settings.discord_guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands to guild {settings.discord_guild_id}")
        else:
            await self.tree.sync()
            logger.info("Synced commands globally")

    async def on_ready(self) -> None:
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("------")


bot = DaijoubuBot()


async def run_bot() -> None:
    """Run the Discord bot."""
    if not settings.discord_bot_token:
        raise ValueError("DISCORD_BOT_TOKEN is not set")

    async with bot:
        await bot.start(settings.discord_bot_token)


def main() -> None:
    """Entry point for the bot."""
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
