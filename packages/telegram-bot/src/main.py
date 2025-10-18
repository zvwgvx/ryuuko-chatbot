# /packages/telegram-bot/src/main.py
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

from . import config
from . import api_client
from .commands import setup_commands

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Main Chat Handler ---
async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text messages and forwards them to the Core API."""
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    text = update.message.text

    logger.info(f"Received message from {user.name} (ID: {user.id}) in chat {chat_id}")

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    # Prepare message for Core API
    messages = [{"role": "user", "content": text}]

    try:
        response_stream = api_client.stream_chat_completions(
            platform="telegram",
            platform_user_id=str(user.id),
            messages=messages
        )
        
        full_response = ""
        async for chunk in response_stream:
            full_response += chunk.decode('utf-8')

        if full_response:
            response_lines = full_response.strip().split('\n')
            for line in response_lines:
                if line.strip():
                    await update.message.reply_text(line.strip())
        else:
            await update.message.reply_text("I received an empty response from the AI. Please try again.")

    except Exception as e:
        logger.error(f"An error occurred in chat_handler: {e}", exc_info=True)
        await update.message.reply_text("Sorry, an internal error occurred. Please try again later.")

# --- Main Application Setup ---
def main() -> None:
    """Starts the Telegram bot."""
    if not config.TELEGRAM_TOKEN:
        logger.critical("TELEGRAM_TOKEN is not set in the environment. Bot cannot start.")
        return

    # CORRECTED: Explicitly set a longer connection timeout to handle slow networks
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=20.0, write_timeout=20.0)
    application = Application.builder().token(config.TELEGRAM_TOKEN).request(request).build()

    # Register the main chat handler for non-command messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

    # Register all commands from the commands/ subpackage
    setup_commands(application)

    logger.info("Telegram bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
