#!/usr/bin/env python3
# coding: utf-8
"""
Discord Bot implementation for Ryuuko Chatbot.
"""
import logging
import sys
import asyncio
import discord
from discord.ext import commands

from bot.config import loader as config_loader
from bot.config import get_user_config_manager
from bot.bot import api as call_api
from bot.bot.commands import register_all_commands
from bot.bot.events import register_all_events
from bot.storage import MemoryStore, get_mongodb_store
from bot.bot.services import auth as auth_service
from bot.utils.health import perform_startup_checks
from bot.utils.queue import get_request_queue

logger = logging.getLogger("Bot.Main")


class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix=".", intents=intents, help_command=None)
        self._register_core_events()
        self._setup_bot_functionality()

    def _register_core_events(self):
        @self.event
        async def on_ready():
            logger.info(f"[OK] Bot is ready: {self.user} (id={self.user.id})")
            logger.info(f"Registered prefix commands: {sorted([c.name for c in self.commands])}")

        @self.event
        async def on_command_error(ctx: commands.Context, error: Exception):
            """Handles common command errors globally."""
            if isinstance(error, commands.CommandNotFound):
                return  # Ignore commands that don't exist.

            if isinstance(error, commands.CheckFailure):
                # User does not have permission to use this command.
                await ctx.send("❌ Bạn không có quyền sử dụng lệnh này.")
            elif isinstance(error, commands.MissingRequiredArgument):
                # A required argument is missing from the command call.
                await ctx.send(f"❌ Thiếu tham số bắt buộc: `{error.param.name}`")
            else:
                # Log any other exceptions and notify the user.
                logger.exception(f"An unexpected error occurred in command '{ctx.command}': {error}")
                await ctx.send("❌ Đã xảy ra lỗi khi thực hiện lệnh.")

    def _setup_bot_functionality(self):
        logger.info("[INIT] Initializing bot modules...")

        mongodb_store = get_mongodb_store()

        # Initialize the MemoryStore with the MongoDB store instance.
        # This allows the MemoryStore to access the database for conversation history.
        memory_store = MemoryStore(mongodb_store)

        user_config_manager = get_user_config_manager()
        request_queue = get_request_queue()
        authorized_users_set = auth_service.load_authorized_users(mongodb_store)

        def add_auth_user_wrapper(user_id: int) -> bool:
            success = auth_service.add_authorized_user(user_id, mongodb_store)
            if success:
                authorized_users_set.add(user_id)
                logger.info(f"In-memory auth set updated: added {user_id}")
            return success

        def remove_auth_user_wrapper(user_id: int) -> bool:
            success = auth_service.remove_authorized_user(user_id, mongodb_store)
            if success:
                authorized_users_set.discard(user_id)
                logger.info(f"In-memory auth set updated: removed {user_id}")
            return success

        dependencies = {
            "config": config_loader,
            "call_api": call_api,
            "user_config_manager": user_config_manager,
            "memory_store": memory_store,
            "mongodb_store": mongodb_store,
            "authorized_users": authorized_users_set,
            "request_queue": request_queue,
            "auth_helpers": {
                'add': add_auth_user_wrapper,
                'remove': remove_auth_user_wrapper,
                'get_set': lambda: authorized_users_set
            }
        }
        register_all_commands(self, dependencies)
        register_all_events(self, dependencies)
        logger.info("[OK] All bot modules initialized successfully.")

    async def _run_startup_checks(self):
        logger.info("[HEALTH] Running pre-startup health checks...")
        if not await perform_startup_checks(config_loader):
            logger.critical("[CRASH] Health checks failed. Bot startup aborted.")
            sys.exit(1)
        logger.info("[OK] All health checks passed!")

    def run(self, token: str, **kwargs):
        async def runner():
            async with self:
                await self._run_startup_checks()
                logger.info("[START] Starting Discord bot...")
                await self.start(token)

        try:
            asyncio.run(runner())
        except (KeyboardInterrupt, SystemExit):
            logger.info("[STOP] Bot shutdown initiated.")
        except Exception as e:
            logger.critical(f"[CRASH] Bot crashed: {e}", exc_info=True)
        finally:
            logger.info("[EXIT] Bot process exiting.")