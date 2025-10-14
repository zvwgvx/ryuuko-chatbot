# /packages/discord-bot/src/commands/user.py
import logging
import discord
from discord.ext import commands

from .. import api_client
from ..utils.embed import send_embed

logger = logging.getLogger("DiscordBot.Commands.User")

def setup_user_commands(bot: commands.Bot, dependencies: dict):
    """Registers user-specific commands that interact with the Core API."""

    @bot.command(name="models")
    async def show_models_command(ctx: commands.Context):
        """Lists all available AI models by fetching from the Core API."""
        all_models = await api_client.list_available_models()
        if all_models is None:
            await send_embed(ctx, title="Error", description="Could not retrieve the list of models from the Core API.", color=discord.Color.red())
            return
        if not all_models:
            await send_embed(ctx, title="No Models Available", description="There are no models configured in the database.", color=discord.Color.blue())
            return

        sorted_models = sorted(
            all_models,
            key=lambda x: (-x.get("access_level", 0), -x.get("credit_cost", 0), x.get("model_name", ""))
        )

        embed = discord.Embed(
            title="Available AI Models",
            description="Models are grouped by access level.",
            color=discord.Color.purple()
        )

        current_level = -1
        field_value = ""
        level_map = {0: "Basic (Lvl 0)", 1: "Advanced (Lvl 1)", 2: "Ultimate (Lvl 2)", 3: "Owner (Lvl 3)"}

        for model in sorted_models:
            access_level = model.get("access_level", 0)
            if access_level != current_level:
                if field_value:
                    embed.add_field(name=level_map.get(current_level, f"Level {current_level}"), value=field_value, inline=False)
                current_level = access_level
                field_value = ""
            
            field_value += f"• `{model.get('model_name', 'N/A')}` ({model.get('credit_cost', 0)} credits)\n"
        
        if field_value:
            embed.add_field(name=level_map.get(current_level, f"Level {current_level}"), value=field_value, inline=False)
        
        await ctx.send(embed=embed)

    @bot.command(name="model")
    async def set_model_command(ctx: commands.Context, *, model: str):
        model_name = model.strip()
        success, message = await api_client.update_user_config(ctx.author.id, model=model_name)
        if success:
            await send_embed(ctx, title="Model Updated", description=f"Your preferred model has been updated to `{model_name}`.", color=discord.Color.green())
        else:
            await send_embed(ctx, title="Update Failed", description=message, color=discord.Color.red())

    @bot.command(name="sysprompt")
    async def set_sys_prompt_command(ctx: commands.Context, *, prompt: str):
        success, message = await api_client.update_user_config(ctx.author.id, system_prompt=prompt)
        if success:
            await send_embed(ctx, title="System Prompt Updated", description="Your custom system prompt has been updated.", color=discord.Color.green())
        else:
            await send_embed(ctx, title="Update Failed", description=message, color=discord.Color.red())

    @bot.command(name="profile")
    async def show_profile_command(ctx: commands.Context, member: discord.Member = None):
        target_user = member or ctx.author
        if target_user != ctx.author and not await bot.is_owner(ctx.author):
            await send_embed(ctx, title="Permission Denied", description="You can only view your own profile.", color=discord.Color.red())
            return

        profile_data = await api_client.get_user_profile(target_user.id)
        if not profile_data:
            await send_embed(ctx, title="Profile Not Found", description=f"Could not retrieve profile for {target_user.display_name}.", color=discord.Color.red())
            return

        model = profile_data.get("model", "Not Set")
        credit = profile_data.get("credit", 0)
        access_level = profile_data.get("access_level", 0)
        level_map = {0: "Basic", 1: "Advanced", 2: "Ultimate", 3: "Owner"}
        level_desc = level_map.get(access_level, "Unknown")

        embed = discord.Embed(title=f"Profile for {target_user.display_name}", color=discord.Color.green())
        if target_user.display_avatar: embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="Current Model", value=f"`{model}`", inline=False)
        embed.add_field(name="Credit Balance", value=str(credit), inline=True)
        embed.add_field(name="Access Level", value=f"{level_desc} (Level {access_level})", inline=True)

        await ctx.send(embed=embed)

    logger.info("User commands have been registered.")
