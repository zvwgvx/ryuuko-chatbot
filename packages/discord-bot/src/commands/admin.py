# /packages/discord-bot/src/commands/admin.py
import logging
import discord
from discord.ext import commands

from .. import api_client
from ..utils.embed import send_embed

logger = logging.getLogger("DiscordBot.Commands.Admin")

# --- New Owner Check ---
def is_ryuuko_owner():
    """
    A command check that verifies if the author of a command is linked
    to a user with owner-level access (level 3) in the Ryuuko dashboard system.
    """
    async def predicate(ctx: commands.Context) -> bool:
        user_profile = await api_client.get_dashboard_user_by_platform_id(
            platform="discord",
            platform_user_id=ctx.author.id
        )
        # Access level 3 is now considered the Owner
        return user_profile and user_profile.get("access_level") == 3
    return commands.check(predicate)

async def get_target_dashboard_id(ctx: commands.Context, member: discord.Member) -> str | None:
    """Helper function to get the dashboard user ID for a given Discord member."""
    target_profile = await api_client.get_dashboard_user_by_platform_id("discord", member.id)
    if not target_profile:
        await send_embed(ctx, title="User Not Linked", description=f"The user {member.mention} has not linked their Discord account to the dashboard.", color=discord.Color.orange())
        return None
    return target_profile.get("id")

def setup_admin_commands(bot: commands.Bot, dependencies: dict):
    """Registers owner-level administrative commands."""

    @bot.command(name="addcredit")
    @is_ryuuko_owner()
    async def add_credit_command(ctx: commands.Context, member: discord.Member, amount: int):
        if amount <= 0:
            await send_embed(ctx, title="Invalid Amount", description="Amount must be a positive number.", color=discord.Color.red())
            return
        
        target_user_id = await get_target_dashboard_id(ctx, member)
        if not target_user_id:
            return

        success, message = await api_client.admin_add_credits(target_user_id, amount)
        if success:
            await send_embed(ctx, title="Credits Added", description=message, color=discord.Color.green())
        else:
            await send_embed(ctx, title="Failed to Add Credits", description=message, color=discord.Color.red())

    @bot.command(name="setcredit")
    @is_ryuuko_owner()
    async def set_credit_command(ctx: commands.Context, member: discord.Member, amount: int):
        if amount < 0:
            await send_embed(ctx, title="Invalid Amount", description="Amount must be a non-negative number.", color=discord.Color.red())
            return
        
        target_user_id = await get_target_dashboard_id(ctx, member)
        if not target_user_id:
            return

        success, message = await api_client.admin_set_credits(target_user_id, amount)
        if success:
            await send_embed(ctx, title="Credits Set", description=message, color=discord.Color.green())
        else:
            await send_embed(ctx, title="Failed to Set Credits", description=message, color=discord.Color.red())

    @bot.command(name="setlevel")
    @is_ryuuko_owner()
    async def set_level_command(ctx: commands.Context, member: discord.Member, level: int):
        if level not in [0, 1, 2, 3]:
            await send_embed(ctx, title="Invalid Level", description="Access level must be 0, 1, 2, or 3.", color=discord.Color.red())
            return
        
        target_user_id = await get_target_dashboard_id(ctx, member)
        if not target_user_id:
            return

        success, message = await api_client.admin_set_level(target_user_id, level)
        if success:
            await send_embed(ctx, title="Access Level Set", description=message, color=discord.Color.green())
        else:
            await send_embed(ctx, title="Failed to Set Level", description=message, color=discord.Color.red())

    logger.info("Owner commands have been registered.")
