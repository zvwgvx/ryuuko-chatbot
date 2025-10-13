# /packages/discord-bot/src/main.py
import logging
import discord
from discord.ext import commands

from . import config
from .utils.queue import get_request_queue
# SỬA LỖI: Import thêm `basic`
from .commands import admin, user, basic
from .events import messages

logger = logging.getLogger("DiscordBot.Main")

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        # SỬA LỖI: Đổi prefix thành '.'
        super().__init__(command_prefix=",", intents=intents, help_command=None)

    async def setup_hook(self) -> None:
        """This is called automatically by discord.py after the bot is logged in."""
        logger.info("[INIT] Initializing client modules inside setup_hook...")
        dependencies = {"request_queue": get_request_queue()}
        
        # SỬA LỖI: Đăng ký các lệnh cơ bản
        admin.setup_admin_commands(self, dependencies)
        user.setup_user_commands(self, dependencies)
        basic.setup_basic_commands(self, dependencies)
        messages.setup_message_events(self, dependencies)
        
        logger.info("[OK] All client modules initialized.")

    async def on_ready(self):
        logger.info(f"[OK] Discord client is ready: {self.user} (id={self.user.id})")

    async def run_client(self):
        if not config.DISCORD_TOKEN:
            logger.critical("DISCORD_TOKEN is not set. The client cannot start.")
            return
        if not config.CORE_API_URL or not config.CORE_API_KEY:
            logger.critical("CORE_API_URL or CORE_API_KEY is not set. The client cannot connect to the Core Service.")
            return
        
        async with self:
            logger.info("[START] Starting Discord client...")
            await self.start(config.DISCORD_TOKEN)
