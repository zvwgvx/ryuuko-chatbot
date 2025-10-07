# src/bot/commands/system.py
"""
Handles owner-only commands for managing system-level configurations,
such as AI models and user credit balances. These commands require a
MongoDB connection to function.
"""
import logging
import discord
from discord.ext import commands

logger = logging.getLogger("Bot.Commands.System")

def setup_system_commands(bot: commands.Bot, mongodb_store):
    """
    Registers owner-only system management commands with the bot.

    Args:
        bot (commands.Bot): The instance of the bot.
        mongodb_store: The instance of the MongoDB data store.
    """
    bot.mongodb_store = mongodb_store

    async def is_mongo_ready(ctx: commands.Context) -> bool:
        """
        A check to ensure that MongoDB is available before executing a command.
        If MongoDB is not available, it sends an error message to the channel.
        """
        if not bot.mongodb_store:
            await ctx.send("❌ This command requires a connection to the MongoDB database, which is not currently configured.")
            return False
        return True

    @bot.command(name="addmodel")
    @commands.is_owner()
    async def add_model_command(ctx: commands.Context, model_name: str, credit_cost: int, access_level: int):
        """Adds a new supported AI model to the database."""
        if not await is_mongo_ready(ctx):
            return
        if credit_cost < 0:
            await ctx.send("❌ Credit cost must be a non-negative number.")
            return
        if access_level not in [0, 1, 2]:
            await ctx.send("❌ Access level must be 0 (Basic), 1 (Advanced), or 2 (Ultimate).")
            return

        success, message = bot.mongodb_store.add_supported_model(model_name, credit_cost, access_level)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    @bot.command(name="removemodel")
    @commands.is_owner()
    async def remove_model_command(ctx: commands.Context, model_name: str):
        """Removes an AI model from the list of supported models."""
        if not await is_mongo_ready(ctx):
            return
        success, message = bot.mongodb_store.remove_supported_model(model_name)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    @bot.command(name="editmodel")
    @commands.is_owner()
    async def edit_model_command(ctx: commands.Context, model_name: str, credit_cost: int, access_level: int):
        """Edits the properties of an existing AI model."""
        if not await is_mongo_ready(ctx):
            return
        if credit_cost < 0:
            await ctx.send("❌ Credit cost must be a non-negative number.")
            return
        if access_level not in [0, 1, 2]:
            await ctx.send("❌ Access level must be 0 (Basic), 1 (Advanced), or 2 (Ultimate).")
            return

        success, message = bot.mongodb_store.edit_supported_model(model_name, credit_cost, access_level)
        await ctx.send(f"✅ {message}" if success else f"❌ {message}")

    @bot.command(name="addcredit")
    @commands.is_owner()
    async def add_credit_command(ctx: commands.Context, member: discord.Member, amount: int):
        """Adds a specified amount of credits to a user's balance."""
        if not await is_mongo_ready(ctx):
            return
        if amount <= 0:
            await ctx.send("❌ The amount of credits to add must be a positive number.")
            return

        success, new_balance = bot.mongodb_store.add_user_credit(member.id, amount)
        if success:
            await ctx.send(f"✅ Added {amount} credits to {member.display_name}. Their new balance is {new_balance}.")
        else:
            await ctx.send(f"❌ Failed to add credits to {member.display_name}.")

    @bot.command(name="deductcredit")
    @commands.is_owner()
    async def deduct_credit_command(ctx: commands.Context, member: discord.Member, amount: int):
        """Deducts a specified amount of credits from a user's balance."""
        if not await is_mongo_ready(ctx):
            return
        if amount <= 0:
            await ctx.send("❌ The amount of credits to deduct must be a positive number.")
            return

        success, new_balance = bot.mongodb_store.deduct_user_credit(member.id, amount)
        if success:
            await ctx.send(f"✅ Deducted {amount} credits from {member.display_name}. Their new balance is {new_balance}.")
        else:
            await ctx.send(f"❌ Failed to deduct credits. This may be due to an insufficient balance or a database error.")

    @bot.command(name="setcredit")
    @commands.is_owner()
    async def set_credit_command(ctx: commands.Context, member: discord.Member, amount: int):
        """Sets a user's credit balance to a specific amount."""
        if not await is_mongo_ready(ctx):
            return
        if amount < 0:
            await ctx.send("❌ Credit balance cannot be set to a negative number.")
            return

        success = bot.mongodb_store.set_user_credit(member.id, amount)
        if success:
            await ctx.send(f"✅ Set {member.display_name}'s credit balance to {amount}.")
        else:
            await ctx.send(f"❌ Failed to set the credit balance for {member.display_name}.")

    @bot.command(name="setlevel")
    @commands.is_owner()
    async def set_level_command(ctx: commands.Context, member: discord.Member, level: int):
        """Sets a user's access level (0, 1, or 2)."""
        if not await is_mongo_ready(ctx):
            return
        if level not in [0, 1, 2]:
            await ctx.send("❌ Access level must be 0 (Basic), 1 (Advanced), or 2 (Ultimate).")
            return

        success = bot.mongodb_store.set_user_level(member.id, level)
        if success:
            level_map = {0: "Basic", 1: "Advanced", 2: "Ultimate"}
            await ctx.send(f"✅ Set {member.display_name}'s access level to {level_map[level]} (Level {level}).")
        else:
            await ctx.send(f"❌ Failed to set the access level for {member.display_name}.")

    logger.info("System commands have been successfully registered.")