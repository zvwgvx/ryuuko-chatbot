# src/core/commands/admin.py
"""
Handles owner-only commands for user management.
"""
import logging
from pathlib import Path
import tempfile
import discord
from discord.ext import commands

logger = logging.getLogger("Core.Commands.Admin")

def setup_admin_commands(bot: commands.Bot, memory_store, auth_helpers: dict):
    """
    Registers owner-only user management commands.

    Args:
        bot (commands.Bot): The bot instance.
        memory_store: The conversation memory store instance.
        auth_helpers (dict): A dict containing functions for auth management.
    """
    bot.memory_store = memory_store
    bot.auth_helpers = auth_helpers

    @bot.command(name="auth")
    @commands.is_owner()
    async def auth_command(ctx: commands.Context, member: discord.Member):
        """Authorizes a user to use the bot."""
        uid = member.id
        if uid in bot.auth_helpers['get_set']():
            await ctx.send(f"❌ User {member.display_name} is already authorized.")
            return

        success = bot.auth_helpers['add'](uid)
        if success:
            await ctx.send(f"✅ Added {member.display_name} to the authorized list.")
        else:
            await ctx.send(f"❌ Failed to add {member.display_name}.")

    @bot.command(name="deauth")
    @commands.is_owner()
    async def deauth_command(ctx: commands.Context, member: discord.Member):
        """Deauthorizes a user."""
        uid = member.id
        if uid not in bot.auth_helpers['get_set']():
            await ctx.send(f"❌ User {member.display_name} is not in the authorized list.")
            return

        success = bot.auth_helpers['remove'](uid)
        if success:
            await ctx.send(f"✅ Removed {member.display_name} from the authorized list.")
        else:
            await ctx.send(f"❌ Failed to remove {member.display_name}.")

    @bot.command(name="auths")
    @commands.is_owner()
    async def show_auth_command(ctx: commands.Context):
        """Shows the list of authorized users."""
        authorized_users = bot.auth_helpers['get_set']()
        if not authorized_users:
            await ctx.send("The authorized users list is empty.")
            return

        body = "\n".join(str(x) for x in sorted(authorized_users))
        if len(body) > 1900:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("Authorized Users:\n" + body)
                temp_path = f.name
            try:
                await ctx.send("The list is too long, sending as a file.", file=discord.File(temp_path, filename="authorized_users.txt"))
            finally:
                Path(temp_path).unlink(missing_ok=True)
        else:
            await ctx.send(f"**Authorized users:**\n{body}")

    @bot.command(name="memory")
    @commands.is_owner()
    async def memory_command(ctx: commands.Context, member: discord.Member = None):
        """Views the recent conversation history of a user."""
        target = member or ctx.author
        if not bot.memory_store:
            await ctx.send("❌ Memory feature is not initialized.")
            return

        mem = bot.memory_store.get_user_messages(target.id)
        if not mem:
            await ctx.send(f"No memory found for {target.display_name}.")
            return

        lines = [f"**Memory for {target.display_name}:**"]
        for i, msg in enumerate(mem[-10:], start=1):
            content = msg.get("content", "[No content]")
            preview = (content[:120] + "…") if len(content) > 120 else content
            lines.append(f"{i:02d}. **{msg.get('role', 'N/A')}**: {preview}")

        await ctx.send("\n".join(lines))

    logger.info("Admin commands have been registered.")