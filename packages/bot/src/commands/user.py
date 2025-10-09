# src/bot/commands/user.py
"""
Handles commands for authorized users to manage their personal settings,
such as their preferred AI model and custom system prompts.
"""
import logging
import discord
from discord.ext import commands

logger = logging.getLogger("Bot.Commands.User")

async def _is_authorized_user(ctx: commands.Context) -> bool:
    """
    A check to determine if the command author is either the bot owner
    or is listed in the set of authorized user IDs.
    """
    if await ctx.bot.is_owner(ctx.author):
        return True
    return ctx.author.id in ctx.bot.authorized_users


def setup_user_commands(bot: commands.Bot, user_config_manager, call_api, memory_store, mongodb_store):
    """
    Registers user-specific configuration commands with the bot.
    """
    bot.user_config_manager = user_config_manager
    bot.call_api = call_api
    bot.memory_store = memory_store
    bot.mongodb_store = mongodb_store

    @bot.command(name="model")
    async def set_model_command(ctx: commands.Context, *, model: str):
        """Sets the user's preferred AI model for conversations."""
        if not await _is_authorized_user(ctx):
            await ctx.send("❌ You are not authorized to use this command.")
            return

        model_name = model.strip()
        is_available, error_message = ctx.bot.call_api.is_model_available(model_name)
        if not is_available:
            await ctx.send(f"❌ {error_message}")
            return

        success, message = ctx.bot.user_config_manager.set_user_model(ctx.author.id, model_name)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    @bot.command(name="sysprompt")
    async def set_sys_prompt_command(ctx: commands.Context, *, prompt: str):
        """Sets a custom system prompt for the user."""
        if not await _is_authorized_user(ctx):
            await ctx.send("❌ You are not authorized to use this command.")
            return

        success, message = ctx.bot.user_config_manager.set_user_system_prompt(ctx.author.id, prompt)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    @bot.command(name="profile")
    async def show_profile_command(ctx: commands.Context, member: discord.Member = None):
        """Displays the configuration profile for a user."""
        target_user = member or ctx.author
        if target_user != ctx.author and not await bot.is_owner(ctx.author):
            await ctx.send("❌ You can only view your own profile.")
            return

        user_config = ctx.bot.user_config_manager.get_user_config(target_user.id)
        model = user_config.get("model", "Default")
        credit = user_config.get("credit", 0)
        access_level = user_config.get("access_level", 0)
        level_map = {0: "Basic", 1: "Advanced", 2: "Ultimate"}
        level_desc = level_map.get(access_level, "Unknown")

        embed = discord.Embed(
            title=f"Profile for {target_user.display_name}", color=discord.Color.green()
        )
        if target_user.display_avatar:
            embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="Current Model", value=f"`{model}`", inline=False)
        embed.add_field(name="Credit Balance", value=str(credit), inline=True)
        embed.add_field(name="Access Level", value=f"{level_desc} (Level {access_level})", inline=True)

        await ctx.send(embed=embed)

    @bot.command(name="showprompt")
    async def show_sys_prompt_command(ctx: commands.Context, member: discord.Member = None):
        """Displays the system prompt for a user."""
        target_user = member or ctx.author
        if target_user != ctx.author and not await bot.is_owner(ctx.author):
            await ctx.send("❌ Only the bot owner can view other users' system prompts.")
            return

        prompt = ctx.bot.user_config_manager.get_user_system_prompt(target_user.id)
        if not prompt:
            await ctx.send(f"{target_user.display_name} does not have a custom system prompt set.")
            return

        if len(prompt) > 1900:
            prompt = prompt[:1900] + "..."
        await ctx.send(f"**System Prompt for {target_user.display_name}:**\n```\n{prompt}\n```")

    @bot.command(name="models")
    async def show_models_command(ctx: commands.Context):
        """Lists all available AI models, categorized by access level."""
        if not bot.mongodb_store:
            supported_models = ctx.bot.user_config_manager.get_supported_models()
            models_list = "\n".join(f"• `{model}`" for model in sorted(supported_models))
            await ctx.send(f"**Supported AI Models (from config file):**\n{models_list}")
            return

        all_models = bot.mongodb_store.list_all_models()
        if not all_models:
            await ctx.send("There are no models configured in the database.")
            return

        sorted_models = sorted(
            all_models,
            key=lambda x: (-x.get("access_level", 0), -x.get("credit_cost", 0), x.get("model_name", ""))
        )
        embed = discord.Embed(
            title="Available AI Models", description="Models are grouped by access level.", color=discord.Color.purple()
        )
        current_level = -1
        field_value = ""
        level_map = {0: "Basic (Lvl 0)", 1: "Advanced (Lvl 1)", 2: "Ultimate (Lvl 2)"}
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

    @bot.command(name="clearmemory")
    async def clearmemory_command(ctx: commands.Context, member: discord.Member = None):
        """Clears the conversation history for a user."""
        target_user = member or ctx.author
        is_owner = await bot.is_owner(ctx.author)

        if target_user != ctx.author and not is_owner:
            await ctx.send("❌ You can only clear your own conversation memory.")
            return

        # An authorized user can clear their own memory.
        # An owner can clear anyone's memory, so they pass this check too.
        if not await _is_authorized_user(ctx) and not is_owner:
            await ctx.send("❌ You are not authorized to use this command.")
            return

        ctx.bot.memory_store.clear_user_messages(target_user.id)
        await ctx.send(f"✅ Cleared conversation memory for {target_user.display_name}.")

    logger.info("User commands have been successfully registered.")