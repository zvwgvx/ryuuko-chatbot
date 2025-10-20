# /packages/telegram-bot/src/main.py
import logging, io, base64
from typing import List, Dict
from PIL import Image

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

# --- Constants (from Discord Bot) ---
IMAGE_MAX_BYTES = 30 * 1024 * 1024
IMAGE_MAX_DIMENSION = 2048

# --- Image Processing & Payload Logic ---
async def _process_telegram_photo(photo: object) -> Dict:
    """Downloads, processes, and base64-encodes a Telegram photo."""
    entry = {"data": None, "mime_type": "image/jpeg", "skipped": False}
    try:
        if photo.file_size > IMAGE_MAX_BYTES:
            logger.warning(f"Image is too large ({photo.file_size} bytes), skipping.")
            return {**entry, "skipped": True}

        file = await photo.get_file()
        image_buffer = io.BytesIO()
        await file.download_to_memory(image_buffer)
        image_buffer.seek(0)

        with Image.open(image_buffer) as img:
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, (0, 0), img.convert('RGBA'))
                img = background
            
            if max(img.width, img.height) > IMAGE_MAX_DIMENSION:
                img.thumbnail((IMAGE_MAX_DIMENSION, IMAGE_MAX_DIMENSION), Image.Resampling.LANCZOS)

            output_buffer = io.BytesIO()
            img.save(output_buffer, format='JPEG', quality=95)
            entry["data"] = base64.b64encode(output_buffer.getvalue()).decode('utf-8')

    except Exception as e:
        logger.exception(f"Failed to process Telegram photo: {e}")
        entry["skipped"] = True
    return entry

def _build_multimodal_content(prompt_text: str, images: List[Dict]) -> List[Dict]:
    """Builds the content payload for a multimodal request."""
    content_parts = []
    if prompt_text:
        content_parts.append({"type": "text", "text": prompt_text})
    for img in images:
        if not img.get("skipped") and img.get("data"):
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:{img['mime_type']};base64,{img['data']}"}
            })
    return content_parts

# --- Main Chat Handler (Text) ---
async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text messages and forwards them to the Core API."""
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    text = update.message.text

    logger.info(f"Received text message from {user.name} (ID: {user.id}) in chat {chat_id}")
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    messages = [{"role": "user", "content": text}]

    try:
        response_stream = api_client.stream_chat_completions(
            platform="telegram", platform_user_id=str(user.id), messages=messages
        )
        full_response = ""
        async for chunk in response_stream:
            full_response += chunk.decode('utf-8')

        if full_response:
            # MODIFIED: Split response by newline and send as separate messages
            response_lines = full_response.strip().split('\n')
            for line in response_lines:
                if line.strip(): # Avoid sending empty messages
                    await update.message.reply_text(line.strip())
        else:
            await update.message.reply_text("I received an empty response. Please try again.")

    except Exception as e:
        logger.error(f"An error occurred in chat_handler: {e}", exc_info=True)
        await update.message.reply_text("Sorry, an internal error occurred.")

# --- Photo Handler ---
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming photos, processes them, and sends to the Core API."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    caption = update.message.caption or ""

    logger.info(f"Received a photo from {user.name} (ID: {user.id}) in chat {chat_id}")
    await context.bot.send_chat_action(chat_id=chat_id, action='upload_photo')

    photo = update.message.photo[-1]
    processed_image = await _process_telegram_photo(photo)

    if processed_image["skipped"]:
        await update.message.reply_text("I couldn't process that image. It might be too large or in an unsupported format.")
        return

    content_payload = _build_multimodal_content(caption, [processed_image])
    if not content_payload:
        await update.message.reply_text("I received an image but couldn't find any content to process.")
        return
    
    messages = [{"role": "user", "content": content_payload}]

    try:
        response_stream = api_client.stream_chat_completions(
            platform="telegram", platform_user_id=str(user.id), messages=messages
        )
        full_response = ""
        async for chunk in response_stream:
            full_response += chunk.decode('utf-8')

        if full_response:
            # MODIFIED: Split response by newline and send as separate messages
            response_lines = full_response.strip().split('\n')
            for line in response_lines:
                if line.strip():
                    await update.message.reply_text(line.strip())
        else:
            await update.message.reply_text("I received an empty response from the AI. Please try again.")

    except Exception as e:
        logger.error(f"An error occurred in photo_handler: {e}", exc_info=True)
        await update.message.reply_text("Sorry, an internal error occurred while processing the image.")

# --- File Handler (Placeholder) ---
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming files/documents and informs the user that they cannot be processed yet."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    file_name = update.message.document.file_name if update.message.document else "a file"
    logger.info(f"Received {file_name} from {user.name} (ID: {user.id}) in chat {chat_id}")
    await update.message.reply_text(f"I've received your file ({file_name}), but I can't process general files yet.")

# --- Main Application Setup ---
def main() -> None:
    """Starts the Telegram bot."""
    if not config.TELEGRAM_TOKEN:
        logger.critical("TELEGRAM_TOKEN is not set in the environment. Bot cannot start.")
        return

    request = HTTPXRequest(connect_timeout=30.0, read_timeout=20.0, write_timeout=20.0)
    application = Application.builder().token(config.TELEGRAM_TOKEN).request(request).build()

    # Register handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, file_handler))

    setup_commands(application)

    logger.info("Telegram bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
