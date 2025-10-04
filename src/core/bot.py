#!/usr/bin/env python3
# coding: utf-8
"""
Discord Bot implementation for Ryuuko Chatbot.

This module provides the main Bot class that encapsulates all Discord bot
functionality, including event handlers, command processing, and lifecycle
management.
"""

import logging
import sys
import os
import asyncio
from typing import Optional, Dict, Any

import discord
from discord.ext import commands

# --- Refactored Imports ---
from src.config import loader as config_loader
from . import call_api

# Import the new registration functions
from src.core.commands import register_all_commands
from src.core.events import register_all_events

# Import managers and auth service
from src.config import get_user_config_manager
from src.utils import get_request_queue
from src.storage import MemoryStore
from src.storage.database import get_mongodb_store
from src.core.services import auth_service

# Import health check
from src.utils.health_check import perform_startup_checks

# Use centralized logger
logger = logging.getLogger("Bot")


class Bot:
    """
    Main Discord bot class that encapsulates all bot functionality.

    This class follows the single responsibility principle by managing
    the Discord bot lifecycle and delegating specific functionality to
    appropriate modules.

    Attributes:
        config: Configuration object containing bot settings
        client: Discord bot client instance
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the bot with configuration.

        Args:
            config: Optional configuration dictionary. If not provided,
                   will use default configuration from loader module.
        """
        self.config = config or {}
        self._client: Optional[commands.Bot] = None
        self._initialized = False

    def _create_bot_instance(self) -> commands.Bot:
        """
        Create and configure the Discord bot instance.

        Returns:
            Configured Discord bot instance with all intents and settings.
        """
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        # Create bot instance
        bot = commands.Bot(
            command_prefix=".",
            intents=intents,
            help_command=None
        )

        # Register core event handlers
        self._register_core_events(bot)

        return bot

    def _register_core_events(self, bot: commands.Bot) -> None:
        """
        Register essential, built-in event handlers for the bot.

        Args:
            bot: Discord bot instance to register events on.
        """

        @bot.event
        async def on_ready():
            """Handle bot ready event."""
            logger.info(
                f"Bot is ready: {bot.user} (id={bot.user.id}) pid={os.getpid()}"
            )
            try:
                cmds = sorted([c.name for c in bot.commands])
                logger.info("Registered prefix commands: %s", cmds)
            except Exception:
                logger.exception("Failed to list commands")

        @bot.event
        async def on_command_error(ctx: commands.Context, error: Exception):
            """
            Handle command errors gracefully.
            """
            if isinstance(error, commands.CommandNotFound):
                return  # Silently ignore unknown commands

            if isinstance(error, commands.CheckFailure):
                await ctx.send(
                    "❌ Bạn không có quyền sử dụng lệnh này.",  # Keep emoji for user
                    allowed_mentions=discord.AllowedMentions.none()
                )
                return

            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(
                    f"❌ Thiếu tham số: {error.param.name}",  # Keep emoji for user
                    allowed_mentions=discord.AllowedMentions.none()
                )
                return

            logger.exception(f"Command error in '{ctx.command}': {error}")
            await ctx.send(
                "❌ Đã xảy ra lỗi khi thực hiện lệnh.",  # Keep emoji for user
                allowed_mentions=discord.AllowedMentions.none()
            )

    def _setup_bot_functionality(self, bot: commands.Bot) -> None:
        """
        NEW: A centralized function to set up all bot functionality by
        initializing dependencies and registering commands/events.
        """
        logger.info("[INIT] Initializing bot modules and functionality...")  # Changed: log only

        # 1. Initialize managers and stores
        config_loader.init_storage()  # Ensure storage paths are ready
        memory_store = MemoryStore()
        user_config_manager = get_user_config_manager()
        request_queue = get_request_queue()
        mongodb_store = get_mongodb_store() if config_loader.USE_MONGODB else None

        # 2. Load data and setup auth service
        authorized_users_set = auth_service.load_authorized_users(config_loader, mongodb_store)

        # 3. Create a single dictionary of all dependencies for injection
        dependencies = {
            "call_api": call_api,
            "config": config_loader,
            "user_config_manager": user_config_manager,
            "request_queue": request_queue,
            "memory_store": memory_store,
            "mongodb_store": mongodb_store,
            "authorized_users": authorized_users_set,
            # Wrap auth functions to pass their own dependencies
            "add_authorized_user": lambda uid: auth_service.add_authorized_user(uid, config_loader, mongodb_store),
            "remove_authorized_user": lambda uid: auth_service.remove_authorized_user(uid, config_loader,
                                                                                      mongodb_store),
        }

        # 4. Register all commands and events, passing the dependencies
        register_all_commands(bot, dependencies)
        register_all_events(bot, dependencies)

        logger.info("[OK] All modules initialized successfully")  # Changed: log only

    def _resolve_token(self) -> str:
        """
        Resolve Discord bot token from various sources.
        """
        token = self.config.get("discord_token") or getattr(config_loader, "DISCORD_TOKEN", None) or os.getenv(
            "DISCORD_TOKEN")
        if not token:
            raise RuntimeError("Discord token not found in config, loader, or environment variables.")
        return token

    def run(self) -> None:
        """
        Start the Discord bot with pre-startup health checks.
        """
        try:
            # Create bot instance if not exists
            if not self._client:
                self._client = self._create_bot_instance()

            # Run health checks before initializing bot functionality
            if not self._initialized:
                logger.info("[HEALTH] Running pre-startup health checks...")  # Changed: log only

                # Create new event loop for health checks
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # Run all health checks
                    health_check_passed = loop.run_until_complete(
                        perform_startup_checks(config_loader)
                    )

                    if not health_check_passed:
                        logger.error("[ERROR] Health checks failed. Bot startup aborted.")  # Changed: log only
                        logger.error("Please fix the issues above and try again.")
                        sys.exit(1)

                    logger.info("[OK] All health checks passed! Proceeding with bot initialization...")  # Changed: log only

                except KeyboardInterrupt:
                    logger.info("[STOP] Health check interrupted by user")  # Changed: log only
                    sys.exit(0)
                except Exception as e:
                    logger.exception("[CRASH] Error during health checks: %s", e)  # Changed: log only
                    sys.exit(1)
                finally:
                    loop.close()

                # Initialize bot functionality after health checks pass
                self._setup_bot_functionality(self._client)
                self._initialized = True

            # Resolve token and start bot
            token = self._resolve_token()
            logger.info("[START] Starting Discord bot...")  # Changed: log only
            self._client.run(token)

        except KeyboardInterrupt:
            logger.info("[STOP] Bot interrupted by user")  # Changed: log only
        except Exception:
            logger.exception("[CRASH] Bot crashed with a critical exception")  # Changed: log only
            raise
        finally:
            logger.info("[EXIT] Bot process exiting")  # Changed: log only


# Module-level function for backward compatibility
def main():
    """Main entry point when running this module directly."""
    bot = Bot()
    bot.run()


if __name__ == "__main__":
    main()