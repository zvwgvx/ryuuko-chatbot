# src/bot/commands/basic.py
"""
Handles basic, universally accessible bot commands such as `ping` and `help`.
"""
import time
import logging
import discord
from discord.ext import commands

logger = logging.getLogger("Bot.Commands.Basic")

def setup_basic_commands(bot: commands.Bot):
    """
    Registers basic informational commands with the bot instance.

    Args:
        bot (commands.Bot): The instance of the bot to which commands will be added.
    """

    @bot.command(name="ping")
    async def ping_command(ctx: commands.Context):
        """
        Measures the bot's latency.

        Calculates both the API response time and the Discord llm_services (WebSocket) latency.
        """
        # Record the time before sending a message to measure response latency.
        start_time = time.perf_counter()
        message = await ctx.send("Pinging...")
        end_time = time.perf_counter()

        # Calculate the time taken for the message to be sent and acknowledged.
        api_latency_ms = round((end_time - start_time) * 1000)
        # Get the bot's WebSocket latency from the discord.py client.
        websocket_latency_ms = round(bot.latency * 1000) if bot.latency is not None else "N/A"

        response_content = (
            f"Pong! 🏓\n"
            f"Response Time: `{api_latency_ms}ms`\n"
            f"WebSocket Latency: `{websocket_latency_ms}ms`"
        )
        await message.edit(content=response_content)

    @bot.command(name="help")
    async def help_command(ctx: commands.Context):
        """
        Displays a list of available commands based on the user's permission level.

        Owners will see a complete list of commands, including administrative ones.
        Regular users will only see the general-purpose commands.
        """
        is_owner = await bot.is_owner(ctx.author)

        # Start with a base embed for better formatting.
        embed = discord.Embed(
            title="Ryuuko Bot Help",
            description="Here are the available commands:",
            color=discord.Color.blue()
        )

        # General user commands
        embed.add_field(
            name="👤 User Commands",
            value=(
                "`ping` - Check bot's latency.\n"
                "`model <model_name>` - Set your preferred AI model.\n"
                "`sysprompt <prompt>` - Set your custom system prompt.\n"
                "`profile [user]` - Show your (or another user's) configuration.\n"
                "`showprompt [user]` - View your (or another user's) system prompt.\n"
                "`models` - List all available AI models.\n"
                "`clearmemory` - Clear your conversation history."
            ),
            inline=False
        )

        if is_owner:
            # Owner-only commands are added if the user is the bot owner.
            embed.add_field(
                name="👑 Owner Commands",
                value=(
                    "`.auth <user>` - Authorize a user.\n"
                    "`.deauth <user>` - De-authorize a user.\n"
                    "`.auths` - List all authorized users.\n"
                    "`.memory [user]` - Inspect a user's conversation memory."
                ),
                inline=False
            )
            embed.add_field(
                name="🛠️ Model Management (Owner)",
                value=(
                    "`.addmodel <name> <cost> <level>` - Add a new model.\n"
                    "`.removemodel <name>` - Remove an existing model.\n"
                    "`.editmodel <name> <cost> <level>` - Edit a model's properties."
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

    logger.info("Basic commands have been successfully registered.")