# /packages/telegram-bot/src/commands/admin.py
import logging
from functools import wraps
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .. import api_client

logger = logging.getLogger(__name__)

# --- Decorator for Owner-Only Commands (Correct Implementation) ---
def is_owner(func):
    """A decorator that restricts a command to users with owner access level (3) via API call."""
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = str(update.effective_user.id)
        
        # Check the user's access level via the API
        profile = await api_client.get_dashboard_user_by_platform_id("telegram", user_id)
        
        if profile and profile.get("access_level") == 3:
            return await func(update, context, *args, **kwargs)
        else:
            logger.warning(f"Unauthorized attempt to use owner command by user {user_id}")
            await update.message.reply_text("You are not authorized to use this command.")
            return

    return wrapped

# --- Helper to get target user --- 
def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> (str, str):
    """Gets the target user's ID and name from a replied-to message or arguments."""
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        return str(target_user.id), target_user.full_name
    elif context.args and len(context.args) > 1:
        # When not replying, the format is /<command> <user_id> <value>
        return context.args[0], context.args[0] # Name is same as ID if not replying
    return None, None

def setup_admin_commands(application: Application, dependencies: dict):
    """Registers administrator-only commands."""

    @is_owner
    async def add_credit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        target_id, target_name = get_target_user(update, context)
        if not target_id or not (context.args and (len(context.args) == 1 if update.message.reply_to_message else len(context.args) > 1)):
            await update.message.reply_text("Usage: Reply to a user and type `/addcredit <amount>` or use `/addcredit <user_id> <amount>`.")
            return

        amount_str = context.args[-1]
        try:
            amount = int(amount_str)
        except ValueError:
            await update.message.reply_text("Invalid amount. Please provide a whole number.")
            return
        
        profile = await api_client.get_dashboard_user_by_platform_id("telegram", target_id)
        if not profile:
            await update.message.reply_text(f"User {target_name} has not linked their account yet.")
            return

        dashboard_user_id = profile['id']
        success, message = await api_client.admin_add_credits(dashboard_user_id, amount)
        await update.message.reply_text(message)

    @is_owner
    async def set_credit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        target_id, target_name = get_target_user(update, context)
        if not target_id or not (context.args and (len(context.args) == 1 if update.message.reply_to_message else len(context.args) > 1)):
            await update.message.reply_text("Usage: Reply to a user and type `/setcredit <amount>` or use `/setcredit <user_id> <amount>`.")
            return

        amount_str = context.args[-1]
        try:
            amount = int(amount_str)
        except ValueError:
            await update.message.reply_text("Invalid amount. Please provide a whole number.")
            return

        profile = await api_client.get_dashboard_user_by_platform_id("telegram", target_id)
        if not profile:
            await update.message.reply_text(f"User {target_name} has not linked their account yet.")
            return

        dashboard_user_id = profile['id']
        success, message = await api_client.admin_set_credits(dashboard_user_id, amount)
        await update.message.reply_text(message)

    @is_owner
    async def set_level_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        target_id, target_name = get_target_user(update, context)
        if not target_id or not (context.args and (len(context.args) == 1 if update.message.reply_to_message else len(context.args) > 1)):
            await update.message.reply_text("Usage: Reply to a user and type `/setlevel <level>` or use `/setlevel <user_id> <level>`.")
            return

        level_str = context.args[-1]
        try:
            level = int(level_str)
            if not 0 <= level <= 3:
                raise ValueError("Level must be between 0 and 3.")
        except ValueError as e:
            await update.message.reply_text(f"Invalid level. {e}")
            return

        profile = await api_client.get_dashboard_user_by_platform_id("telegram", target_id)
        if not profile:
            await update.message.reply_text(f"User {target_name} has not linked their account yet.")
            return

        dashboard_user_id = profile['id']
        success, message = await api_client.admin_set_level(dashboard_user_id, level)
        await update.message.reply_text(message)

    application.add_handler(CommandHandler("addcredit", add_credit_command))
    application.add_handler(CommandHandler("setcredit", set_credit_command))
    application.add_handler(CommandHandler("setlevel", set_level_command))

    logger.info("Admin commands have been registered.")
