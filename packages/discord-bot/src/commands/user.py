# /packages/discord-bot/src/commands/user.py
import logging
import discord
from discord.ext import commands
from typing import List, Dict, Any

from .. import api_client
from ..utils.embed import send_embed

logger = logging.getLogger("DiscordBot.Commands.User")

# --- Plan Name Mapping ---
PLAN_MAP = {
    0: "Basic",
    1: "Advanced",
    2: "Ultimate",
    3: "Owner"
}

# --- Helper to render message content ---
def render_message_content(content: Any) -> str:
    """Renders complex message content into a simple string for Discord embeds."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if part.get('type') == 'text':
                parts.append(part.get('text', ''))
            elif part.get('type') == 'image_url':
                parts.append("[Image]")
        return "\n".join(parts)
    return "[Unsupported Content]"

def setup_user_commands(bot: commands.Bot, dependencies: dict):
    """Registers user commands for account management."""

    @bot.command(name="link")
    async def link_command(ctx: commands.Context, code: str):
        """Links your Discord account to your dashboard account using a code."""
        try: await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound, discord.HTTPException): pass

        avatar_url = str(ctx.author.avatar.url) if ctx.author.avatar else None
        success, message = await api_client.link_account(
            code=code,
            platform="discord",
            platform_user_id=str(ctx.author.id),
            display_name=ctx.author.name,
            avatar_url=avatar_url
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

    # --- Memory Commands ---

    @bot.command(name="memory")
    async def memory_command(ctx: commands.Context):
        """Shows the last 10 messages in your conversation history."""
        success, memory = await api_client.get_memory("discord", str(ctx.author.id))

        if not success:
            error_content = memory[0]["content"] if memory else "An unknown error occurred."
            await send_embed(ctx, title="Error Fetching Memory", description=error_content, color=discord.Color.red())
            return

        if not memory:
            await send_embed(ctx, title="Memory is Empty", description="You have no conversation history stored.", color=discord.Color.blue())
            return

        embed = discord.Embed(title="Recent Conversation Memory", color=discord.Color.blue())
        description_parts = []
        
        for msg in memory[-10:]:
            raw_role = msg.get("role", "unknown")
            role = "You" if raw_role == "user" else "Ryuuko" if raw_role == "assistant" else raw_role.capitalize()
            
            content = render_message_content(msg.get("content", ""))
            sanitized_content = content.replace("`", "'").replace("\n", " ")
            
            description_parts.append(f"**{role}**: `{sanitized_content}`")

        full_description = "\n".join(description_parts)
        if len(full_description) > 4096:
            full_description = full_description[:4093] + "..."
        
        embed.description = full_description
        embed.set_footer(text=f"Showing last {len(memory[-10:])} of {len(memory)} messages.")
        await ctx.send(embed=embed)

    @bot.command(name="clear")
    async def clear_command(ctx: commands.Context):
        """Permanently clears your entire conversation history."""
        async with ctx.typing():
            success, message = await api_client.clear_memory("discord", str(ctx.author.id))

            if success:
                await send_embed(ctx, title="Memory Cleared", description=message, color=discord.Color.green())
            else:
                await send_embed(ctx, title="Clearing Failed", description=message, color=discord.Color.red())

    # --- Model Commands ---

    @bot.command(name="models")
    async def models_command(ctx: commands.Context):
        """Lists all available AI models you can choose from."""
        logger.info(f"`.models` command invoked by {ctx.author.name}")
        success, models = await api_client.get_available_models()
        
        if not success:
            logger.error("API call to get_available_models failed.")
            await send_embed(ctx, title="Error", description="Could not fetch the list of available models.", color=discord.Color.red())
            return
        
        logger.info(f"Successfully fetched {len(models)} models from the API.")

        grouped_models = {}
        for model in models:
            level = model.get("access_level", 0)
            if level not in grouped_models:
                grouped_models[level] = []
            grouped_models[level].append(model)

        embed = discord.Embed(title="Available AI Models", description="Use `.model <name>` to set your preference.", color=discord.Color.purple())
        
        if not grouped_models:
            embed.description = "No models are currently available."
        else:
            for level in sorted(grouped_models.keys(), reverse=True):
                plan_name = PLAN_MAP.get(level, "Unknown Tier")
                model_list = "\n".join([f"- `{m['model_name']}`" for m in grouped_models[level]])
                embed.add_field(name=f"**{plan_name} Models**", value=model_list, inline=False)

        await ctx.send(embed=embed)
        logger.info("Sent `.models` embed to user.")

    @bot.command(name="model")
    async def model_command(ctx: commands.Context, *, model_name: str = None):
        """Sets your preferred AI model for future conversations."""
        logger.info(f"`.model` command invoked by {ctx.author.name} with argument: '{model_name}'")
        if not model_name:
            await send_embed(ctx, title="Usage", description="Please provide a model name. Example: `.model ryuuko-r1-vnm-mini`", color=discord.Color.orange())
            return

        async with ctx.typing():
            success, message = await api_client.set_user_model("discord", str(ctx.author.id), model_name)
            if success:
                logger.info(f"Successfully set model for {ctx.author.name} to '{model_name}'. API response: {message}")
                await send_embed(ctx, title="Model Updated", description=f"Your preferred model has been set to `{model_name}`.", color=discord.Color.green())
            else:
                logger.error(f"Failed to set model for {ctx.author.name}. API response: {message}")
                await send_embed(ctx, title="Update Failed", description=message, color=discord.Color.red())

    logger.info("User commands (link, unlink, profile, memory, clear, models, model) have been registered.")
