# src/bot/commands/system.py
"""
Handles owner-only commands for system management (models, credits).
Requires MongoDB.
"""
import logging
import discord
from discord.ext import commands

logger = logging.getLogger("Bot.Commands.System")


def setup_system_commands(bot: commands.Bot, mongodb_store):
    """
    Registers owner-only system management commands.

    Args:
        bot (commands.Bot): The bot instance.
        mongodb_store: The MongoDB store instance.
    """
    bot.mongodb_store = mongodb_store

    def is_mongo_ready(ctx) -> bool:
        """Check if MongoDB is configured."""
        if not bot.mongodb_store:
            # This is an async context, so we need to create a task
            async def send_msg():
                await ctx.send("❌ This feature requires MongoDB to be configured.")

            bot.loop.create_task(send_msg())
            return False
        return True

    @bot.command(name="addmodel")
    @commands.is_owner()
    async def add_model_command(ctx: commands.Context, model_name: str, credit_cost: int, access_level: int):
        """Adds a new model to the database."""
        if not is_mongo_ready(ctx): return
        if credit_cost < 0:
            await ctx.send("❌ Credit cost must be non-negative.")
            return
        if access_level not in [0, 1, 2]:
            await ctx.send("❌ Access level must be 0 (Basic), 1 (Advanced), or 2 (Ultimate).")
            return

        success, message = bot.mongodb_store.add_supported_model(model_name, credit_cost, access_level)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    @bot.command(name="removemodel")
    @commands.is_owner()
    async def remove_model_command(ctx: commands.Context, model_name: str):
        """Removes a model from the database."""
        if not is_mongo_ready(ctx): return
        success, message = bot.mongodb_store.remove_supported_model(model_name)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    @bot.command(name="editmodel")
    @commands.is_owner()
    async def edit_model_command(ctx: commands.Context, model_name: str, credit_cost: int, access_level: int):
        """Edits an existing model in the database."""
        if not is_mongo_ready(ctx): return
        if credit_cost < 0:
            await ctx.send("❌ Credit cost must be non-negative.")
            return
        if access_level not in [0, 1, 2]:
            await ctx.send("❌ Access level must be 0 (Basic), 1 (Advanced), or 2 (Ultimate).")
            return

        success, message = bot.mongodb_store.edit_supported_model(model_name, credit_cost, access_level)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    @bot.command(name="addcredit")
    @commands.is_owner()
    async def add_credit_command(ctx: commands.Context, member: discord.Member, amount: int):
        """Adds credits to a user."""
        if not is_mongo_ready(ctx): return
        if amount <= 0:
            await ctx.send("❌ Amount must be positive.")
            return

        success, new_balance = bot.mongodb_store.add_user_credit(member.id, amount)
        if success:
            await ctx.send(f"✅ Added {amount} credits to {member.display_name}. New balance: {new_balance}")
        else:
            await ctx.send("❌ Failed to add credits.")

    @bot.command(name="deductcredit")
    @commands.is_owner()
    async def deduct_credit_command(ctx: commands.Context, member: discord.Member, amount: int):
        """Deducts credits from a user."""
        if not is_mongo_ready(ctx): return
        if amount <= 0:
            await ctx.send("❌ Amount must be positive.")
            return

        success, new_balance = bot.mongodb_store.deduct_user_credit(member.id, amount)
        if success:
            await ctx.send(f"✅ Deducted {amount} credits from {member.display_name}. New balance: {new_balance}")
        else:
            await ctx.send("❌ Failed to deduct credits (insufficient balance or error).")

    @bot.command(name="setcredit")
    @commands.is_owner()
    async def set_credit_command(ctx: commands.Context, member: discord.Member, amount: int):
        """Sets a user's credit balance."""
        if not is_mongo_ready(ctx): return
        if amount < 0:
            await ctx.send("❌ Amount must be non-negative.")
            return

        success = bot.mongodb_store.set_user_credit(member.id, amount)
        if success:
            await ctx.send(f"✅ Set {member.display_name}'s credit balance to {amount}.")
        else:
            await ctx.send("❌ Failed to set credits.")

    @bot.command(name="setlevel")
    @commands.is_owner()
    async def set_level_command(ctx: commands.Context, member: discord.Member, level: int):
        """Sets a user's access level."""
        if not is_mongo_ready(ctx): return
        if level not in [0, 1, 2]:
            await ctx.send("❌ Level must be 0 (Basic), 1 (Advanced), or 2 (Ultimate).")
            return

        success = bot.mongodb_store.set_user_level(member.id, level)
        if success:
            level_map = {0: "Basic", 1: "Advanced", 2: "Ultimate"}
            await ctx.send(f"✅ Set {member.display_name}'s access level to {level_map[level]} (Level {level}).")
        else:
            await ctx.send("❌ Failed to set user level.")

    logger.info("System commands have been registered.")