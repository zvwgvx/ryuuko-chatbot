# src/bot/commands/user_config.py
"""
Handles commands for authorized users to manage their personal settings.
"""
import logging
import discord
from discord.ext import commands

logger = logging.getLogger("Bot.Commands.User")

async def _is_authorized_user(ctx: commands.Context) -> bool:
    """Helper to check if the user is authorized or the bot owner."""
    if await ctx.bot.is_owner(ctx.author):
        return True
    return ctx.author.id in ctx.bot.authorized_users


def setup_user_commands(bot: commands.Bot, user_config_manager, call_api, memory_store, mongodb_store):
    """
    Registers user-specific configuration commands.

    Args:
        bot (commands.Bot): The bot instance.
        user_config_manager: The manager for user configurations.
        call_api: The API client module.
        memory_store: The conversation memory store instance.
        mongodb_store: The MongoDB store instance (can be None).
    """
    # Attach dependencies to the bot object for access within commands
    bot.user_config_manager = user_config_manager
    bot.call_api = call_api
    bot.memory_store = memory_store
    bot.mongodb_store = mongodb_store

    @bot.command(name="model")
    async def set_model_command(ctx: commands.Context, *, model: str):
        """Sets the user's preferred AI model."""
        if not await _is_authorized_user(ctx):
            await ctx.send("❌ You are not authorized to use this command.")
            return

        available, error = ctx.bot.call_api.is_model_available(model.strip())
        if not available:
            await ctx.send(f"❌ {error}")
            return

        success, message = ctx.bot.user_config_manager.set_user_model(ctx.author.id, model.strip())
        await ctx.send(f"✅ {message}")

    @bot.command(name="sysprompt")
    async def set_sys_prompt_command(ctx: commands.Context, *, prompt: str):
        """Sets the user's custom system prompt."""
        if not await _is_authorized_user(ctx):
            await ctx.send("❌ You are not authorized to use this command.")
            return

        success, message = ctx.bot.user_config_manager.set_user_system_prompt(ctx.author.id, prompt)
        await ctx.send(f"✅ {message}")

    @bot.command(name="profile")
    async def show_profile_command(ctx: commands.Context, member: discord.Member = None):
        """Shows the configuration profile for a user."""
        target_user = member or ctx.author
        if target_user != ctx.author and not await bot.is_owner(ctx.author):
            await ctx.send("❌ You can only view your own profile.")
            return

        user_config = ctx.bot.user_config_manager.get_user_config(target_user.id)
        model = user_config.get("model", "Not set")
        credit = user_config.get("credit", 0)
        access_level = user_config.get("access_level", 0)
        level_map = {0: "Basic", 1: "Advanced", 2: "Ultimate"}
        level_desc = level_map.get(access_level, "Unknown")

        lines = [
            f"**Profile for {target_user.display_name}:**",
            f"**Current Model**: `{model}`",
            f"**Credit Balance**: {credit}",
            f"**Access Level**: {level_desc} (Level {access_level})",
        ]
        await ctx.send("\n".join(lines))

    @bot.command(name="showprompt")
    async def show_sys_prompt_command(ctx: commands.Context, member: discord.Member = None):
        """Shows the system prompt for a user."""
        target_user = member or ctx.author
        if target_user != ctx.author and not await bot.is_owner(ctx.author):
            await ctx.send("❌ Only the bot owner can view other users' system prompts.")
            return

        prompt = ctx.bot.user_config_manager.get_user_system_message(target_user.id)
        if len(prompt) > 1900:
            prompt = prompt[:1900] + "..."
        await ctx.send(f"**System Prompt for {target_user.display_name}:**\n```\n{prompt}\n```")

    @bot.command(name="models")
    async def show_models_command(ctx: commands.Context):
        """Shows all available AI models."""
        if bot.mongodb_store:
            all_models = bot.mongodb_store.list_all_models()
            if not all_models:
                await ctx.send("No models found in the database.")
                return

            lines = ["**Available AI Models:**"]

            # Sort models: First by access_level (descending), then by credit_cost (descending)
            sorted_models = sorted(
                all_models,
                key=lambda x: (
                    -x.get("access_level", 0),  # Higher level first
                    -x.get("credit_cost", 0),  # Higher cost first within same level
                    x.get("model_name", "")  # Alphabetical as tiebreaker
                )
            )

            current_level = -1
            for model in sorted_models:
                access_level = model.get("access_level", 0)
                if access_level != current_level:
                    level_map = {0: "Basic", 1: "Advanced", 2: "Ultimate"}
                    lines.append(f"\n**{level_map.get(access_level, f'Level {access_level}')} Models:**")
                    current_level = access_level
                lines.append(f"• `{model.get('model_name', 'N/A')}` - {model.get('credit_cost', 0)} credits")

            await ctx.send("\n".join(lines))
        else:
            supported_models = ctx.bot.user_config_manager.get_supported_models()
            models_list = "\n".join(f"• `{model}`" for model in sorted(supported_models))
            await ctx.send(f"**Supported AI Models (from file):**\n{models_list}")

    @bot.command(name="clearmemory")
    async def clearmemory_command(ctx: commands.Context, member: discord.Member = None):
        """Clears the conversation history for a user."""
        target_user = member or ctx.author
        if target_user != ctx.author and not await bot.is_owner(ctx.author):
            await ctx.send("❌ You can only clear your own memory.")
            return
        if target_user == ctx.author and not await _is_authorized_user(ctx):
            await ctx.send("❌ You are not authorized to use this command.")
            return

        ctx.bot.memory_store.clear_user(target_user.id)
        await ctx.send(f"✅ Cleared conversation memory for {target_user.display_name}.")

    logger.info("User commands have been registered.")