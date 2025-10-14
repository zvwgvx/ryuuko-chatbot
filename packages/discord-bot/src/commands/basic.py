# /packages/discord-bot/src/commands/basic.py
import time
import logging
import discord
import asyncio
import re
from typing import Optional
from discord.ext import commands

from ..utils.embed import send_embed

logger = logging.getLogger("DiscordBot.Commands.Basic")

async def measure_external_ping(host: str) -> Optional[float]:
    """Measures the latency to an external host using the system's ping command."""
    try:
        process = await asyncio.create_subprocess_shell(
            f"ping -c 1 {host}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            match = re.search(r"time=([\d.]+)\s*ms", stdout.decode())
            if match:
                return float(match.group(1))
    except (FileNotFoundError, Exception) as e:
        logger.error(f"Ping measurement failed for {host}: {e}")
    return None

def setup_basic_commands(bot: commands.Bot, dependencies: dict):
    """Registers basic informational commands with the bot."""

    @bot.command(name="ping")
    async def ping_command(ctx: commands.Context):
        """Measures the bot's latency to Google, Cloudflare, and Discord."""
        embed = discord.Embed(title="Pinging... 🏓", description="Measuring latencies...", color=discord.Color.blue())
        message = await ctx.send(embed=embed)

        # Measure latencies concurrently
        google_task = asyncio.create_task(measure_external_ping("8.8.8.8"))
        cloudflare_task = asyncio.create_task(measure_external_ping("1.1.1.1"))
        
        websocket_latency_ms = round(bot.latency * 1000) if bot.latency is not None else None

        # Wait for external pings to complete
        google_latency, cloudflare_latency = await asyncio.gather(google_task, cloudflare_task)
        
        # Format results
        ws_latency_str = f"`{websocket_latency_ms}ms`" if websocket_latency_ms is not None else "N/A"
        gg_latency_str = f"`{round(google_latency)}ms`" if google_latency is not None else "Failed"
        cf_latency_str = f"`{round(cloudflare_latency)}ms`" if cloudflare_latency is not None else "Failed"

        final_embed = discord.Embed(
            title="Pong! 🏓",
            description=(
                f"**Google DNS:** {gg_latency_str}\n"
                f"**Cloudflare DNS:** {cf_latency_str}\n"
                f"**Discord WebSocket:** {ws_latency_str}"
            ),
            color=discord.Color.blue()
        )
        await message.edit(embed=final_embed)

    @bot.command(name="help")
    async def help_command(ctx: commands.Context):
        """Displays a list of available commands."""
        is_owner = await bot.is_owner(ctx.author)

        embed = discord.Embed(
            title="Ryuuko Bot Help",
            description="Here are the available commands:",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="👤 User Commands",
            value=(
                "`.ping` - Check bot's latency.\n"
                "`.help` - Shows this help message.\n"
                "`.models` - Lists all available AI models.\n"
                "`.model <name>` - Set your preferred AI model.\n"
                "`.sysprompt <prompt>` - Set your custom system prompt.\n"
                "`.profile [user]` - Show your configuration profile.\n"
                "`.clearmemory` - Clear your conversation history."
            ),
            inline=False
        )

        if is_owner:
            embed.add_field(
                name="👑 Owner Commands",
                value=(
                    "`.auth <user>` - Authorize a user.\n"
                    "`.deauth <user>` - De-authorize a user.\n"
                    "`.auths` - List all authorized users.\n"
                    "`.clearmemory [user]` - Clear a user's conversation memory."
                ),
                inline=False
            )
            embed.add_field(
                name="🛠️ Model Management (Owner)",
                value=(
                    "`.addmodel <name> <cost> <level>` - Add a new model.\n"
                    "`.removemodel <name>` - Remove an existing model."
                ),
                inline=False
            )
            embed.add_field(
                name="💰 Credit & Access Management (Owner)",
                value=(
                    "`.addcredit <user> <amount>` - Add credits to a user.\n"
                    "`.deductcredit <user> <amount>` - Deduct credits from a user.\n"
                    "`.setcredit <user> <amount>` - Set a user's credit balance.\n"
                    "`.setlevel <user> <level>` - Set a user's access level."
                ),
                inline=False
            )

        await ctx.send(embed=embed)

    logger.info("Basic commands have been registered.")
