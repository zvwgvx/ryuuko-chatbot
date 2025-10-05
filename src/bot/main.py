#!/usr/bin/env python3
# coding: utf-8
"""
Discord Bot implementation for Ryuuko Chatbot.
"""

import logging
import sys
import os
import asyncio
from typing import Optional

import discord
from discord.ext import commands

# --- Refactored Imports ---
# Import the unified config loader directly
from src.config import loader as config_loader
from src.config import get_user_config_manager

# Import API client functions
from src.bot import api as call_api

# Import registration functions
from src.bot.commands import register_all_commands
from src.bot.events import register_all_events

# Import managers and services
from src.storage import MemoryStore
from src.storage.database import get_mongodb_store
from src.bot.services import auth as auth_service
from src.utils.health import perform_startup_checks
from src.utils.queue import get_request_queue

# Use centralized logger
logger = logging.getLogger("Bot.Main")


class Bot(commands.Bot):
    """
    Main Discord bot class, inheriting directly from commands.Bot for simplicity.
    """

    def __init__(self):
        # 1. Initialize the parent class (commands.Bot) with intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        # Call the parent constructor
        super().__init__(command_prefix=".", intents=intents, help_command=None)

        # 2. Register core, built-in event handlers
        self._register_core_events()

        # 3. Setup all other bot functionality (commands, custom events, etc.)
        self._setup_bot_functionality()

    def _register_core_events(self):
        """Register essential, built-in event handlers for the bot."""

        @self.event
        async def on_ready():
            """Handle bot ready event."""
            logger.info(f"[OK] Bot is ready: {self.user} (id={self.user.id})")
            try:
                cmds = sorted([c.name for c in self.commands])
                logger.info(f"Registered prefix commands: {cmds}")
            except Exception:
                logger.exception("Failed to list commands")

        @self.event
        async def on_command_error(ctx: commands.Context, error: Exception):
            """Handle command errors gracefully."""
            if isinstance(error, commands.CommandNotFound):
                return  # Silently ignore unknown commands

            if isinstance(error, commands.CheckFailure):
                await ctx.send("❌ Bạn không có quyền sử dụng lệnh này.")
                return

            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(f"❌ Thiếu tham số bắt buộc: `{error.param.name}`")
                return

            logger.exception(f"Command error in '{ctx.command}': {error}")
            await ctx.send("❌ Đã xảy ra lỗi khi thực hiện lệnh.")

    def _setup_bot_functionality(self):
        """
        A centralized function to set up all bot functionality by
        initializing dependencies and registering commands/events.
        """
        logger.info("[INIT] Initializing bot modules...")

        # Initialize managers and stores
        memory_store = MemoryStore()
        user_config_manager = get_user_config_manager()
        mongodb_store = get_mongodb_store()
        request_queue = get_request_queue()

        # Load authorized users
        authorized_users_set = auth_service.load_authorized_users(mongodb_store)

        # Create a single dictionary of all dependencies for injection
        dependencies = {
            "config": config_loader, # <<< THÊM DÒNG NÀY
            "call_api": call_api,
            "user_config_manager": user_config_manager,
            "memory_store": memory_store,
            "mongodb_store": mongodb_store,
            "authorized_users": authorized_users_set,
            "request_queue": request_queue,
            "auth_helpers": {
                'add': lambda uid: auth_service.add_authorized_user(uid, mongodb_store),
                'remove': lambda uid: auth_service.remove_authorized_user(uid, mongodb_store),
                'get_set': lambda: authorized_users_set
            }
        }

        # Register all commands and events, passing the dependencies
        register_all_commands(self, dependencies)
        register_all_events(self, dependencies)

        logger.info("[OK] All bot modules initialized successfully.")

    async def _run_startup_checks(self):
        """Run pre-startup health checks in an async context."""
        logger.info("[HEALTH] Running pre-startup health checks...")
        if not await perform_startup_checks(config_loader):
            logger.critical("[CRASH] Health checks failed. Bot startup aborted.")
            sys.exit(1)
        logger.info("[OK] All health checks passed!")

    def run(self, token: str, **kwargs):
        """
        Override the default run method to include startup checks.
        """

        async def runner():
            # Use 'async with' which is the recommended way to run the bot
            async with self:
                await self._run_startup_checks()
                logger.info("[START] Starting Discord bot...")
                await self.start(token)

        try:
            # Run the async runner
            asyncio.run(runner())
        except KeyboardInterrupt:
            logger.info("[STOP] Bot interrupted by user.")
        except Exception as e:
            logger.critical(f"[CRASH] Bot crashed with a critical exception: {e}", exc_info=True)
            sys.exit(1)
        finally:
            logger.info("[EXIT] Bot process exiting.")
