# src/core/commands/basic.py
"""
Handles basic bot commands like ping and help.
"""
import time
import logging
import discord
from discord.ext import commands

logger = logging.getLogger("Core.Commands.Basic")

def setup_basic_commands(bot: commands.Bot):
    """
    Registers basic informational commands with the bot.

    Args:
        bot (commands.Bot): The bot instance.
    """

    @bot.command(name="ping")
    async def ping_command(ctx: commands.Context):
        """Checks the bot's latency."""
        start_time = time.perf_counter()
        msg = await ctx.send("Pinging...")
        end_time = time.perf_counter()

        latency_ms = round((end_time - start_time) * 1000)
        ws_latency = round(bot.latency * 1000) if bot.latency else "N/A"

        content = f"Pong! \nResponse: {latency_ms} ms\nWebSocket: {ws_latency} ms"
        await msg.edit(content=content)

    @bot.command(name="help")
    async def help_command(ctx: commands.Context):
        """Shows the available commands based on user permissions."""
        is_owner = await bot.is_owner(ctx.author)

        lines = [
            "**Available commands:**",
            "`.ping` – Check bot responsiveness",
            "",
            "**Configuration commands (authorized users):**",
            "`.model <model>` – Set your preferred AI model",
            "`.sysprompt <prompt>` – Set your system prompt",
            "`.profile [user]` – Show user configuration",
            "`.showprompt [user]` – View system prompt",
            "`.models` – Show all supported models",
            "`.clearmemory [user]` – Clear conversation history",
        ]

        if is_owner:
            lines += [
                "",
                "**Owner‑only commands:**",
                "`.auth <user>` – Add a user to authorized list",
                "`.deauth <user>` – Remove user from authorized list",
                "`.auths` – List authorized users",
                "`.memory [user]` – View conversation history",
                "",
                "**Model management (owner only):**",
                "`.addmodel <name> <cost> <level>` – Add a new model",
                "`.removemodel <name>` – Remove a model",
                "`.editmodel <name> <cost> <level>` – Edit model settings",
                "",
                "**Credit management (owner only):**",
                "`.addcredit <user> <amount>` – Add credits to user",
                "`.deductcredit <user> <amount>` – Deduct credits from user",
                "`.setcredit <user> <amount>` – Set user's credit balance",
                "`.setlevel <user> <level>` – Set user access level (0-3)"
            ]

        await ctx.send("\n".join(lines))

    logger.info("Basic commands have been registered.")