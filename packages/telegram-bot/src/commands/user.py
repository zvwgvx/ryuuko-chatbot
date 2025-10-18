# /packages/telegram-bot/src/commands/user.py
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from typing import Any

from .. import api_client
from .. import config # Import config to get TELEGRAM_TOKEN

logger = logging.getLogger(__name__)

# --- Plan Name Mapping ---
PLAN_MAP = {
    0: "Basic",
    1: "Advanced",
    2: "Ultimate",
    3: "Owner"
}

# --- Helper to render message content for Telegram ---
def render_telegram_message_content(content: Any) -> str:
    """Renders complex message content into a simple string for Telegram messages."""
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

def setup_user_commands(application: Application, dependencies: dict):
    """Registers user-specific commands."""

    async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        profile = await api_client.get_dashboard_user_by_platform_id("telegram", user.id)
        if not profile:
            await update.message.reply_text("Your account is not linked. Use the /link command to link your account.")
            return

        plan_name = PLAN_MAP.get(profile.get("access_level", 0), "Unknown")
        message = (
            f"<b>👤 Profile for {user.first_name}</b>\n\n"
            f"<b>Username:</b> {profile.get('username', 'N/A')}\n"
            f"<b>Plan:</b> {plan_name}\n"
            f"<b>Credit Balance:</b> {profile.get('credit', 0):,}"
        )
        await update.message.reply_html(message)

    async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"[Telegram Bot] /link command received from user {user.id}")

        if not context.args:
            logger.warning(f"[Telegram Bot] /link command: No code provided by user {user.id}")
            await update.message.reply_text("Please provide a link code. Usage: /link <code>")
            return
        
        code = context.args[0]
        logger.info(f"[Telegram Bot] /link command: Code received: {code}")

        avatar_url = None
        try:
            photos = await context.bot.get_user_profile_photos(user.id, limit=1)
            if photos and photos.photos:
                # CORRECTED: Construct the full public URL for the avatar
                file = await context.bot.get_file(photos.photos[0][-1].file_id)
                if file.file_path and config.TELEGRAM_TOKEN:
                    avatar_url = f"https://api.telegram.org/file/bot{config.TELEGRAM_TOKEN}/{file.file_path}"
            logger.info(f"[Telegram Bot] /link command: Avatar URL retrieved: {avatar_url}")
        except Exception as e:
            logger.warning(f"[Telegram Bot] Could not retrieve profile photo for {user.id}: {e}")

        success, message = await api_client.link_account(
            code=code,
            platform="telegram",
            platform_user_id=str(user.id),
            display_name=user.full_name,
            avatar_url=avatar_url
        )
        logger.info(f"[Telegram Bot] /link command: API response - Success: {success}, Message: {message}")

        try:
            await update.message.reply_text(message)
            logger.info(f"[Telegram Bot] /link command: Successfully sent reply to user {user.id}")
        except Exception as e:
            logger.error(f"[Telegram Bot] Error sending reply to user {user.id} for /link command: {e}", exc_info=True)

    async def unlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        success, message = await api_client.unlink_account("telegram", str(user.id))
        await update.message.reply_text(message)

    async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        success, memory = await api_client.get_memory("telegram", str(user.id))

        if not success or not memory:
            await update.message.reply_text("Your conversation memory is empty.")
            return

        message_parts = ["<b>Memory (Last 10 Messages)</b>\n"]
        for msg in memory[-10:]:
            role = "You" if msg.get("role") == "user" else "Ryuuko"
            content = render_telegram_message_content(msg.get("content", ""))
            message_parts.append(f"<b>{role}:</b> {content}")
        
        await update.message.reply_html("\n".join(message_parts))

    async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        success, message = await api_client.clear_memory("telegram", str(user.id))
        await update.message.reply_text(message)

    async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        success, models = await api_client.get_available_models()
        if not success or not models:
            await update.message.reply_text("Could not fetch the list of available models.")
            return

        grouped = {}
        for model in models:
            level = model.get("access_level", 0)
            if level not in grouped: grouped[level] = []
            grouped[level].append(model)

        message = "<b>Available AI Models</b>\n<i>Use /model &lt;name&gt; to set your preference.</i>\n"
        for level in sorted(grouped.keys(), reverse=True):
            plan_name = PLAN_MAP.get(level, "Unknown Tier")
            model_list = "\n".join([f"- <code>{m['model_name']}</code>" for m in grouped[level]])
            message += f"\n<b>{plan_name} Models</b>\n{model_list}"
        
        await update.message.reply_html(message)

    async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not context.args:
            await update.message.reply_text("Please provide a model name. Usage: /model <model_name>")
            return
        
        model_name = " ".join(context.args)
        success, message = await api_client.set_user_model("telegram", str(user.id), model_name)
        
        if success:
            await update.message.reply_html(f"Your preferred model has been set to <code>{model_name}</code>.")
        else:
            await update.message.reply_text(message)

    # Register all handlers
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("link", link_command))
    application.add_handler(CommandHandler("unlink", unlink_command))
    application.add_handler(CommandHandler("memory", memory_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("models", models_command))
    application.add_handler(CommandHandler("model", model_command))

    logger.info("User commands have been registered.")
