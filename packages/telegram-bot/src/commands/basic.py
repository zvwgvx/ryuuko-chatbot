# /packages/telegram-bot/src/commands/basic.py
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

from .. import api_client # Import api_client to check permissions

# A hardcoded version number for debugging purposes
BOT_CODE_VERSION = "v2.3.2"

logger = logging.getLogger(__name__)

def setup_basic_commands(application: Application, dependencies: dict):
    """Registers basic, general-purpose commands."""

    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Displays a comprehensive list of available commands."""
        user = update.effective_user

        # --- User Commands ---
        user_cmds = (
            "<b>👤 User Commands</b>\n"
            "/profile - Displays your linked account profile.\n"
            "/link &lt;code&gt; - Links your Telegram to your dashboard account.\n"
            "/unlink - Unlinks your Telegram account.\n"
            "/memory - Shows the last 10 messages in your history.\n"
            "/clear - Permanently clears your conversation history.\n"
            "/models - Lists all available AI models.\n"
            "/model &lt;name&gt; - Sets your preferred AI model."
        )

        # --- Admin Commands (Show only to owner based on API access_level) ---
        admin_cmds = ""
        profile = await api_client.get_dashboard_user_by_platform_id("telegram", user.id)
        if profile and profile.get("access_level") == 3:
            admin_cmds = (
                "\n<b>👑 Admin Commands</b> (Reply to a user's message to target them)\n"
                "/addcredit &lt;amount&gt; - Adds credits to the user.\n"
                "/setcredit &lt;amount&gt; - Sets the user's credit balance.\n"
                "/setlevel &lt;level&gt; - Sets the user's access level (0-3)."
            )

        footer = f"<i>Ryuuko {BOT_CODE_VERSION} | Talk to me in private chat!</i>"
        
        full_message = f"{user_cmds}{admin_cmds}\n\n{footer}"
        
        await update.message.reply_html(full_message)

    async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Checks the bot's latency (not a real network ping)."""
        await update.message.reply_text("Pong!")

    async def version_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Displays the current running code version of the bot."""
        await update.message.reply_html(f"Currently running code version: <code>{BOT_CODE_VERSION}</code>")

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", start_command)) # Alias for /start
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("version", version_command))

    logger.info("Basic commands (start, help, ping, version) have been registered.")
