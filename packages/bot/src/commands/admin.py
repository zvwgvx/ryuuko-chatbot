# src/bot/commands/admin.py
"""
Handles owner-only commands for bot administration and user management.

This module includes commands for:
- Authorizing and de-authorizing users.
- Listing authorized users.
- Inspecting user conversation history (memory).
"""
import logging
from pathlib import Path
import tempfile
import discord
from discord.ext import commands

logger = logging.getLogger("Bot.Commands.Admin")

def setup_admin_commands(bot: commands.Bot, memory_store, auth_helpers: dict):
    """
    Registers owner-only administrative commands with the bot.

    Args:
        bot (commands.Bot): The instance of the bot.
        memory_store: The instance of the conversation memory store.
        auth_helpers (dict): A dictionary of helper functions for authorization management.
    """
    bot.memory_store = memory_store
    bot.auth_helpers = auth_helpers

    @bot.command(name="auth")
    @commands.is_owner()
    async def auth_command(ctx: commands.Context, member: discord.Member):
        """Authorizes a specific user to interact with the bot."""
        user_id = member.id
        if user_id in bot.auth_helpers['get_set']():
            await ctx.send(f"❌ User {member.display_name} is already authorized.")
            return

        success = bot.auth_helpers['add'](user_id)
        if success:
            await ctx.send(f"✅ Added {member.display_name} to the authorized user list.")
        else:
            await ctx.send(f"❌ An error occurred while trying to authorize {member.display_name}.")

    @bot.command(name="deauth")
    @commands.is_owner()
    async def deauth_command(ctx: commands.Context, member: discord.Member):
        """De-authorizes a user, revoking their access."""
        user_id = member.id
        if user_id not in bot.auth_helpers['get_set']():
            await ctx.send(f"❌ User {member.display_name} is not on the authorized list.")
            return

        success = bot.auth_helpers['remove'](user_id)
        if success:
            await ctx.send(f"✅ Removed {member.display_name} from the authorized user list.")
        else:
            await ctx.send(f"❌ An error occurred while trying to de-authorize {member.display_name}.")

    @bot.command(name="auths")
    @commands.is_owner()
    async def show_auth_command(ctx: commands.Context):
        """Shows the complete list of authorized user IDs."""
        authorized_users = bot.auth_helpers['get_set']()
        if not authorized_users:
            await ctx.send("The authorized users list is currently empty.")
            return

        user_list_str = "\n".join(str(uid) for uid in sorted(authorized_users))

        if len(user_list_str) > 1900:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_f:
                temp_f.write("Authorized User IDs:\n" + user_list_str)
                temp_path = temp_f.name

            try:
                await ctx.send("The list of authorized users is too long to display, sending it as a file.", file=discord.File(temp_path, filename="authorized_users.txt"))
            finally:
                Path(temp_path).unlink(missing_ok=True)
        else:
            await ctx.send(f"**Authorized User IDs:**\n```\n{user_list_str}\n```")

    @bot.command(name="memory")
    @commands.is_owner()
    async def memory_command(ctx: commands.Context, member: discord.Member = None):
        """
        Inspects the recent conversation history for a user.

        If no user is specified, it shows the history of the command author.
        """
        target_user = member or ctx.author
        if not bot.memory_store:
            await ctx.send("❌ The memory store is not initialized.")
            return

        messages = bot.memory_store.get_user_messages(target_user.id)
        if not messages:
            await ctx.send(f"No conversation memory found for {target_user.display_name}.")
            return

        # THAY ĐỔI: Ánh xạ role sang tên thân mật
        role_map = {
            "user": "You",
            "assistant": "Ryuuko"
        }

        lines = [f"**Conversation Memory for {target_user.display_name}:**"]
        for i, msg in enumerate(messages[-10:], start=1):
            content = msg.get("content", "[Message content not available]")
            preview = (content[:120] + "…") if len(content) > 120 else content
            
            # Sử dụng role_map để lấy tên hiển thị
            role_name = msg.get('role', 'N/A')
            display_name = role_map.get(role_name, role_name.capitalize())
            
            lines.append(f"`{i:02d}.` **{display_name}**: {preview}")

        await ctx.send("\n".join(lines))

    logger.info("Admin commands have been successfully registered.")
