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
from typing import Optional, Dict, Any

import discord
from discord.ext import commands

from src.config import loader
from . import call_api
from . import functions

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

        # Register event handlers
        self._register_events(bot)

        return bot

    def _register_events(self, bot: commands.Bot) -> None:
        """
        Register all event handlers for the bot.

        Args:
            bot: Discord bot instance to register events on.
        """

        @bot.event
        async def on_ready():
            """Handle bot ready event."""
            logger.info(
                f"Bot is ready: {bot.user} (id={bot.user.id}) pid={os.getpid()}"
            )

            # Log registered commands
            try:
                cmds = sorted([c.name for c in bot.commands])
                logger.info("Registered prefix commands: %s", cmds)
            except Exception:
                logger.exception("Failed to list commands")

            # Inspect on_message listeners
            try:
                listeners = list(
                    getattr(bot, "_listeners", {}).get("on_message", [])
                )
                logger.info(
                    "on_message listeners (count=%d): %s",
                    len(listeners),
                    [
                        f"{getattr(l, '__module__', '?')}:"
                        f"{getattr(l, '__qualname__', '?')} id={hex(id(l))}"
                        for l in listeners
                    ]
                )
            except Exception:
                logger.exception("Failed to inspect listeners")

        @bot.event
        async def on_command_error(ctx: commands.Context, error: Exception):
            """
            Handle command errors gracefully.

            Args:
                ctx: Command context
                error: Exception that occurred
            """
            if isinstance(error, commands.CommandNotFound):
                return  # Silently ignore unknown commands

            if isinstance(error, commands.CheckFailure):
                await ctx.send(
                    "❌ Bạn không có quyền sử dụng lệnh này.",
                    allowed_mentions=discord.AllowedMentions.none()
                )
                return

            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(
                    f"❌ Thiếu tham số: {error.param}",
                    allowed_mentions=discord.AllowedMentions.none()
                )
                return

            logger.exception(f"Command error in {ctx.command}: {error}")
            await ctx.send(
                "❌ Đã xảy ra lỗi khi thực hiện lệnh.",
                allowed_mentions=discord.AllowedMentions.none()
            )

    def _initialize_modules(self, bot: commands.Bot) -> None:
        """
        Initialize all bot modules and extensions.

        Args:
            bot: Discord bot instance to initialize modules for.
        """
        logger.info("🔧 Initializing functions module...")
        functions.setup(bot, call_api, loader)
        logger.info("✅ All modules initialized successfully")

    def _resolve_token(self) -> str:
        """
        Resolve Discord bot token from various sources.

        Token resolution order:
        1. config['discord_token'] (dict access)
        2. loader.DISCORD_TOKEN
        3. Environment variable DISCORD_TOKEN

        Returns:
            Discord bot token

        Raises:
            RuntimeError: If no token can be found
        """
        token = None

        # Try to get from config dict first
        if self.config and isinstance(self.config, dict):
            token = self.config.get("discord_token")

        # Fallback to loader module
        if not token:
            token = getattr(loader, "DISCORD_TOKEN", None)

        # Final fallback to environment variable
        if not token:
            token = os.getenv("DISCORD_TOKEN")

        if not token:
            raise RuntimeError(
                "Discord token not found. Please provide token via:\n"
                "- config['discord_token']\n"
                "- loader.DISCORD_TOKEN\n"
                "- Environment variable DISCORD_TOKEN"
            )

        return token

    def run(self) -> None:
        """
        Start the Discord bot.

        This method will block until the bot is shut down.

        Raises:
            RuntimeError: If token cannot be resolved
            Exception: Any exception from Discord.py during runtime
        """
        try:
            # Create bot instance if not exists
            if not self._client:
                self._client = self._create_bot_instance()

            # Initialize modules only once
            if not self._initialized:
                self._initialize_modules(self._client)
                self._initialized = True

            # Resolve token and start bot
            token = self._resolve_token()
            logger.info("🚀 Starting bot...")
            self._client.run(token)

        except KeyboardInterrupt:
            logger.info("🛑 Bot interrupted by user")
        except Exception as e:
            logger.exception("💥 Bot crashed with exception")
            raise
        finally:
            logger.info("👋 Bot process exiting")


# Module-level function for backward compatibility
def main():
    """
    Main entry point when running this module directly.

    This function is kept for backward compatibility and testing purposes.
    """
    bot = Bot()
    bot.run()


if __name__ == "__main__":
    main()