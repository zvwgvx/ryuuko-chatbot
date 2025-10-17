# /packages/discord-bot/src/commands/user.py
import logging
import discord
from discord.ext import commands

from .. import api_client
from ..utils.embed import send_embed

logger = logging.getLogger("DiscordBot.Commands.User")

# --- Plan Name Mapping ---
PLAN_MAP = {
    0: "Basic",
    1: "Advanced",
    2: "Ultimate",
    3: "Owner" # Changed from Admin
}

def setup_user_commands(bot: commands.Bot, dependencies: dict):
    """Registers user commands for account management."""

    @bot.command(name="link")
    async def link_command(ctx: commands.Context, code: str):
        """Links your Discord account to your dashboard account using a code."""
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass

        success, message = await api_client.link_account(
            code=code,
            platform="discord",
            platform_user_id=str(ctx.author.id),
            display_name=ctx.author.name
        )

        if success:
            await send_embed(ctx, title="Account Linked Successfully", description=message, color=discord.Color.green())
        else:
            await send_embed(ctx, title="Linking Failed", description=message, color=discord.Color.red())

    @bot.command(name="unlink")
    async def unlink_command(ctx: commands.Context):
        """Unlinks your Discord account from the dashboard."""
        profile = await api_client.get_dashboard_user_by_platform_id("discord", ctx.author.id)
        if not profile:
            await send_embed(ctx, title="Not Linked", description="Your account is not currently linked.", color=discord.Color.orange())
            return

        success, message = await api_client.unlink_account(
            platform="discord",
            platform_user_id=str(ctx.author.id)
        )

        if success:
            await send_embed(ctx, title="Account Unlinked", description=message, color=discord.Color.green())
        else:
            await send_embed(ctx, title="Unlinking Failed", description=message, color=discord.Color.red())
    
    @bot.command(name="profile")
    async def profile_command(ctx: commands.Context):
        """Displays your linked profile information."""
        profile = await api_client.get_dashboard_user_by_platform_id("discord", ctx.author.id)
        if not profile:
            await send_embed(ctx, title="Profile Not Found", description="Your account is not linked. Use the `.link` command to link your account.", color=discord.Color.orange())
            return

        embed = discord.Embed(title=f"Profile for {ctx.author.display_name}", color=discord.Color.blue())
        if ctx.author.display_avatar:
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
        access_level = profile.get("access_level", 0)
        plan_name = PLAN_MAP.get(access_level, "Unknown")

        embed.add_field(name="Username", value=profile.get("username", "N/A"), inline=True)
        embed.add_field(name="Plan", value=plan_name, inline=True)
        embed.add_field(name="Credit Balance", value=f"{profile.get('credit', 0):,}", inline=True)

        linked_accounts = profile.get("linked_accounts", [])
        if linked_accounts:
            linked_str = "\n".join([f"- {acc.get('platform').capitalize()}: `{acc.get('platform_display_name')}`" for acc in linked_accounts])
            embed.add_field(name="Linked Accounts", value=linked_str, inline=False)

        await ctx.send(embed=embed)

    logger.info("User commands (link, unlink, profile) have been registered.")
