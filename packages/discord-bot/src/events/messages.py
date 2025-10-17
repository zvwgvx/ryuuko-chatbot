# /packages/discord-bot/src/events/messages.py
import re, logging, asyncio, base64, io
from pathlib import Path
from typing import List, Dict
import discord
from discord.ext import commands
from PIL import Image

from .. import api_client
from ..utils.embed import send_embed

logger = logging.getLogger("DiscordBot.Events.Messages")

# --- Constants ---
IMAGE_MAX_BYTES = 30 * 1024 * 1024
IMAGE_MAX_DIMENSION = 2048
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp", "image/bmp"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

# --- Attachment & Payload Logic (Correct and unchanged) ---
async def _read_image_attachment(attachment: discord.Attachment) -> Dict:
    entry = {"filename": attachment.filename, "data": None, "mime_type": None, "skipped": False}
    try:
        if attachment.size > IMAGE_MAX_BYTES: return {**entry, "skipped": True}
        if not (attachment.content_type in ALLOWED_IMAGE_MIMES or (Path(attachment.filename).suffix or "").lower() in ALLOWED_IMAGE_EXTENSIONS): return {**entry, "skipped": True}
        image_data = await attachment.read()
        with Image.open(io.BytesIO(image_data)) as img:
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = Image.new('RGB', img.size, (255, 255, 255)); background.paste(img, (0, 0), img.convert('RGBA')); img = background
            if max(img.width, img.height) > IMAGE_MAX_DIMENSION: img.thumbnail((IMAGE_MAX_DIMENSION, IMAGE_MAX_DIMENSION), Image.Resampling.LANCZOS)
            output_buffer = io.BytesIO(); img.save(output_buffer, format='JPEG', quality=95)
            entry["data"] = base64.b64encode(output_buffer.getvalue()).decode('utf-8'); entry["mime_type"] = "image/jpeg"
    except Exception as e: logger.exception(f"Failed to process image {attachment.filename}: {e}"); entry["skipped"] = True
    return entry

def _build_multimodal_content(prompt_text: str, images: List[Dict]) -> List[Dict]:
    content_parts = []
    image_queue = [img for img in images if not img.get("skipped")]
    text_segments = re.split(r'\s*\[ảnh\]\s*|\[ảnh\]', prompt_text)
    for i, segment in enumerate(text_segments):
        if segment: content_parts.append({"type": "text", "text": segment})
        if i < len(text_segments) - 1 and image_queue:
            img = image_queue.pop(0); content_parts.append({"type": "image_url", "image_url": {"url": f"data:{img['mime_type']};base64,{img['data']}", "detail": "auto"}})
    while image_queue:
        img = image_queue.pop(0); content_parts.append({"type": "image_url", "image_url": {"url": f"data:{img['mime_type']};base64,{img['data']}", "detail": "auto"}})
    return content_parts

# --- Main Event Setup Function ---
def setup_message_events(bot: commands.Bot, dependencies: dict):

    async def handle_ai_prompt(message: discord.Message):
        # This function remains the same.
        try:
            async with message.channel.typing():
                user_profile = await api_client.get_dashboard_user_by_platform_id("discord", message.author.id)
                if not user_profile:
                    await send_embed(message.channel, title="Account Not Linked", description="To use Ryuuko, you must first link your Discord account to the dashboard.\n\nPlease visit the dashboard, log in, and follow the instructions to link your account.", color=discord.Color.orange(), reference=message)
                    return
                user_text = re.sub(rf"<@!?{bot.user.id}>", "", message.content or "").strip()
                image_attachments = [att for att in (message.attachments or []) if att.content_type in ALLOWED_IMAGE_MIMES or (Path(att.filename).suffix or "").lower() in ALLOWED_IMAGE_EXTENSIONS]
                processed_images = await asyncio.gather(*[_read_image_attachment(att) for att in image_attachments])
                user_message_content = _build_multimodal_content(user_text, processed_images)
                if not user_message_content and not user_text: return
                messages_payload = [{"role": "user", "content": user_message_content or user_text}]
                response_message, full_response_text = None, ""
                async for chunk in api_client.stream_chat_completions(platform="discord", platform_user_id=str(message.author.id), messages=messages_payload):
                    chunk_text = chunk.decode('utf-8', errors='ignore')
                    if chunk_text.startswith("Error:"): await message.channel.send(f"⚠️ {chunk_text}", reference=message); return
                    full_response_text += chunk_text
                    if response_message is None:
                        if full_response_text.strip(): response_message = await message.channel.send(full_response_text, reference=message)
                    else:
                        if response_message.content != full_response_text and full_response_text.strip(): await response_message.edit(content=full_response_text)
                if not full_response_text.strip(): await message.channel.send("⚠️ The AI returned an empty response.", reference=message)
        except Exception as e:
            logger.exception(f"Error processing AI prompt for user {message.author.id}")
            await message.channel.send(f"⚠️ An unexpected error occurred: {e}", reference=message)

    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return

        # This is the crucial part. We let discord.py process commands first.
        # This will find and execute commands if the message is a valid command.
        # If not, it will do nothing, and we can proceed.
        await bot.process_commands(message)

        # After the library has tried to process commands, we check if a command was actually found.
        # If a command was found, we don't want to also treat it as a chat message.
        ctx = await bot.get_context(message)
        if ctx.valid: # .valid is True if a command was found, even if it failed checks.
            return

        # If no command was found, THEN we can safely treat it as a potential AI prompt.
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mention = bot.user in message.mentions
        
        if is_dm or is_mention:
            # It's not a command, but it is a DM or mention, so treat as AI prompt.
            asyncio.create_task(handle_ai_prompt(message))

    logger.info("[OK] Final, most reliable message event listener has been registered.")
