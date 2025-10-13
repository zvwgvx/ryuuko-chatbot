# /packages/discord-bot/src/commands/basic.py
import time
import logging
import discord
from discord.ext import commands

logger = logging.getLogger("DiscordBot.Commands.Basic")

def setup_basic_commands(bot: commands.Bot, dependencies: dict):
    """Registers basic informational commands with the bot."""

    @bot.command(name="ping")
    async def ping_command(ctx: commands.Context):
        """Measures the bot's latency."""
        start_time = time.perf_counter()
        message = await ctx.send("Pinging...")
        end_time = time.perf_counter()
        api_latency_ms = round((end_time - start_time) * 1000)
        websocket_latency_ms = round(bot.latency * 1000) if bot.latency is not None else "N/A"
        response_content = (
            f"Pong! 🏓\n"
            f"Response Time: `{api_latency_ms}ms`\n"
            f"WebSocket Latency: `{websocket_latency_ms}ms`"
        )
        await message.edit(content=response_content)

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
            # SỬA LỖI: Thêm lệnh deductcredit vào help
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
