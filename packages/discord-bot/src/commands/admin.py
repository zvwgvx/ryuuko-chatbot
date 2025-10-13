# /packages/discord-bot/src/commands/admin.py
import logging
import discord
import json
from discord.ext import commands

from .. import api_client

logger = logging.getLogger("DiscordBot.Commands.Admin")

def setup_admin_commands(bot: commands.Bot, dependencies: dict):
    """Registers owner-only administrative commands that interact with the Core API."""

    # --- Authorization Commands ---
    @bot.command(name="auth")
    @commands.is_owner()
    async def auth_command(ctx: commands.Context, member: discord.Member):
        success, message = await api_client.add_authorized_user(member.id)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    @bot.command(name="deauth")
    @commands.is_owner()
    async def deauth_command(ctx: commands.Context, member: discord.Member):
        success, message = await api_client.remove_authorized_user(member.id)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    @bot.command(name="auths")
    @commands.is_owner()
    async def show_auth_command(ctx: commands.Context):
        authorized_users = await api_client.get_authorized_users()
        if authorized_users is None: await ctx.send("❌ Failed to retrieve authorized users list."); return
        if not authorized_users: await ctx.send("The authorized users list is empty."); return
        user_list_str = "\n".join(str(uid) for uid in sorted(authorized_users))
        await ctx.send(f"**Authorized User IDs:**\n```\n{user_list_str}\n```")

    # --- Model Management ---
    @bot.command(name="addmodel")
    @commands.is_owner()
    async def add_model_command(ctx: commands.Context, model_name: str, credit_cost: int, access_level: int):
        success, message = await api_client.add_model(model_name, credit_cost, access_level)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    @bot.command(name="removemodel")
    @commands.is_owner()
    async def remove_model_command(ctx: commands.Context, model_name: str):
        success, message = await api_client.remove_model(model_name)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    # --- Credit & Level Management ---
    @bot.command(name="addcredit")
    @commands.is_owner()
    async def add_credit_command(ctx: commands.Context, member: discord.Member, amount: int):
        if amount <= 0: await ctx.send("❌ Amount must be a positive number."); return
        success, message = await api_client.add_user_credits(member.id, amount)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    # --- SỬA LỖI: Implement lại lệnh deductcredit ---
    @bot.command(name="deductcredit")
    @commands.is_owner()
    async def deduct_credit_command(ctx: commands.Context, member: discord.Member, amount: int):
        if amount <= 0: await ctx.send("❌ Amount must be a positive number."); return
        success, message = await api_client.deduct_user_credits(member.id, amount)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    @bot.command(name="setcredit")
    @commands.is_owner()
    async def set_credit_command(ctx: commands.Context, member: discord.Member, amount: int):
        if amount < 0: await ctx.send("❌ Amount must be a non-negative number."); return
        success, message = await api_client.set_user_credits(member.id, amount)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    @bot.command(name="setlevel")
    @commands.is_owner()
    async def set_level_command(ctx: commands.Context, member: discord.Member, level: int):
        if level not in [0, 1, 2, 3]: await ctx.send("❌ Access level must be 0, 1, 2, or 3."); return
        success, message = await api_client.set_user_level(member.id, level)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    # --- Memory Management ---
    @bot.command(name="memory")
    @commands.is_owner()
    async def memory_command(ctx: commands.Context, member: discord.Member = None):
        target_user = member or ctx.author
        messages = await api_client.get_user_memory(target_user.id)
        if messages is None: await ctx.send(f"❌ Could not retrieve memory for {target_user.display_name}."); return
        if not messages: await ctx.send(f"No conversation memory found for {target_user.display_name}."); return

        role_map = {"user": "You", "assistant": "Ryuuko"}
        lines = [f"**Conversation Memory for {target_user.display_name}:**"]
        for i, msg in enumerate(messages[-10:], start=1):
            role_name = msg.get('role', 'N/A')
            display_name = role_map.get(role_name, role_name.capitalize())
            content = msg.get("content", "[No content]")
            preview = ""
            if isinstance(content, str):
                preview = (content[:120] + "…") if len(content) > 120 else content
            elif isinstance(content, list):
                text_parts = [part.get("text", "") for part in content if part.get("type") == "text"]
                image_parts = [part.get("type") for part in content if part.get("type") == "image_url"]
                preview = " ".join(text_parts).strip()
                if len(preview) > 90: preview = preview[:90] + "…"
                if image_parts: preview += f" `[+{len(image_parts)} image(s)]`"
            lines.append(f"`{i:02d}.` **{display_name}**: {preview or '[Empty Content]'}")
        await ctx.send("\n".join(lines))

    @bot.command(name="clearmemory")
    @commands.is_owner()
    async def clearmemory_command(ctx: commands.Context, member: discord.Member = None):
        target_user = member or ctx.author
        success = await api_client.clear_user_memory(target_user.id)
        if success:
            await ctx.send(f"✅ Successfully sent request to clear memory for {target_user.display_name}.")
        else:
            await ctx.send(f"❌ Failed to send request to clear memory for {target_user.display_name}.")

    logger.info("Admin commands have been registered.")
