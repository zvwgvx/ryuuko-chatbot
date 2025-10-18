# /packages/discord-bot/src/commands/basic.py
import logging
import discord
from discord.ext import commands

from ..utils.embed import send_embed

logger = logging.getLogger("DiscordBot.Commands.Basic")

# A hardcoded version number for debugging purposes
BOT_CODE_VERSION = "v2.3.3"

def setup_basic_commands(bot: commands.Bot, dependencies: dict):
    """Registers basic, general-purpose commands."""

    @bot.command(name="help")
    async def help_command(ctx: commands.Context):
        """Displays a comprehensive list of available commands."""
        embed = discord.Embed(
            title="Ryuuko Bot Commands",
            description="Here is a list of commands you can use.",
            color=discord.Color.blue()
        )

        # User Commands
        user_cmds = """
        `,profile` - Displays your linked account profile.
        `,link <code>` - Links your Discord to your dashboard account.
        `,unlink` - Unlinks your Discord account.
        `,memory` - Shows the last 10 messages in your history.
        `,clear` - Permanently clears your conversation history.
        `,models` - Lists all available AI models.
        `,model <name>` - Sets your preferred AI model.
        """
        embed.add_field(name="👤 User Commands", value=user_cmds, inline=False)

        # Owner Commands (Only show to the owner)
        try:
            from . import admin # Local import to avoid circular dependency
            is_owner = await commands.check(admin.is_ryuuko_owner()).predicate(ctx)
        except Exception:
            is_owner = False
        
        if is_owner:
            owner_cmds = """
            `,addcredit <@user> <amount>` - Adds credits to a user.
            `,setcredit <@user> <amount>` - Sets a user's credit balance.
            `,setlevel <@user> <level>` - Sets a user's access level (0-3).
            """
            embed.add_field(name="👑 Owner Commands", value=owner_cmds, inline=False)

        embed.set_footer(text=f"Ryuuko {BOT_CODE_VERSION} | Use commands in DMs or by mentioning the bot.")
        await ctx.send(embed=embed)

    @bot.command(name="ping")
    async def ping_command(ctx: commands.Context):
        """Checks the bot's latency."""
        latency = bot.latency * 1000  # Convert to milliseconds
        await send_embed(ctx, "Ping", f"Pong! Latency is {latency:.2f}ms.", discord.Color.green())

    @bot.command(name="version")
    async def version_command(ctx: commands.Context):
        """(DEBUG) Displays the current running code version of the bot."""
        await send_embed(ctx, "Bot Version", f"Currently running code version: `{BOT_CODE_VERSION}`", discord.Color.purple())

    logger.info(f"Basic commands have been registered (Code Version: {BOT_CODE_VERSION})")
