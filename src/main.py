#!/usr/bin/env python3
# coding: utf-8

import logging
import sys
import os

from discord.ext import commands
import discord

import load_config
import call_api
import functions

# logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("Main")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

@bot.event
async def on_ready():
    logger.info(f"Bot is ready: {bot.user} (id={bot.user.id}) pid={os.getpid()}")

    # show registered commands
    try:
        cmds = sorted([c.name for c in bot.commands])
        logger.info("Registered prefix commands: %s", cmds)
    except Exception:
        logger.exception("Failed to list commands")

    # inspect on_message listeners
    try:
        listeners = list(getattr(bot, "_listeners", {}).get("on_message", []))
        logger.info("on_message listeners (count=%d): %s", len(listeners),
                    [f"{getattr(l, '__module__', '?')}:{getattr(l, '__qualname__', '?')} id={hex(id(l))}" for l in
                     listeners])
    except Exception:
        logger.exception("Failed to inspect listeners")


# Initialize functions module
logger.info("🔧 Initializing functions module...")
functions.setup(bot, call_api, load_config)

# Add error handler for commands
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands

    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này.", allowed_mentions=discord.AllowedMentions.none())
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Thiếu tham số: {error.param}", allowed_mentions=discord.AllowedMentions.none())
        return

    logger.exception(f"Command error in {ctx.command}: {error}")
    await ctx.send("❌ Đã xảy ra lỗi khi thực hiện lệnh.", allowed_mentions=discord.AllowedMentions.none())


if __name__ == "__main__":
    try:
        logger.info("🚀 Starting bot...")
        bot.run(load_config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrupted by user")
    except Exception:
        logger.exception("💥 Bot exited with exception")
    finally:
        logger.info("👋 Main process exiting")