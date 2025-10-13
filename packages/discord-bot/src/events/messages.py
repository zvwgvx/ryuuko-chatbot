# /packages/discord-bot/src/events/messages.py
import re, json, logging, asyncio, base64, mimetypes, io
from pathlib import Path
from typing import List, Dict, Any
import discord
from discord.ext import commands
from PIL import Image

from .. import api_client

logger = logging.getLogger("DiscordBot.Events.Messages")

# --- Constants ---
IMAGE_MAX_BYTES = 30 * 1024 * 1024
IMAGE_MAX_DIMENSION = 2048
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp", "image/bmp"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

# --- Attachment & Payload Logic ---
async def _read_image_attachment(attachment: discord.Attachment) -> Dict:
    entry = {"filename": attachment.filename, "data": None, "mime_type": None, "skipped": False}
    try:
        if attachment.size > IMAGE_MAX_BYTES: return {**entry, "skipped": True}
        if not (attachment.content_type in ALLOWED_IMAGE_MIMES or (Path(attachment.filename).suffix or "").lower() in ALLOWED_IMAGE_EXTENSIONS): return {**entry, "skipped": True}
        
        image_data = await attachment.read()
        with Image.open(io.BytesIO(image_data)) as img:
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, (0, 0), img.convert('RGBA'))
                img = background
            if max(img.width, img.height) > IMAGE_MAX_DIMENSION:
                img.thumbnail((IMAGE_MAX_DIMENSION, IMAGE_MAX_DIMENSION), Image.Resampling.LANCZOS)
            
            output_buffer = io.BytesIO()
            img.save(output_buffer, format='JPEG', quality=95)
            entry["data"] = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
            entry["mime_type"] = "image/jpeg"
    except Exception as e:
        logger.exception(f"Failed to process image {attachment.filename}: {e}")
        entry["skipped"] = True
    return entry

def _build_multimodal_content(prompt_text: str, images: List[Dict]) -> List[Dict]:
    content_parts = []
    image_queue = [img for img in images if not img.get("skipped")]
    text_segments = re.split(r'\s*\[ảnh\]\s*|\[ảnh\]', prompt_text)
    for i, segment in enumerate(text_segments):
        if segment: content_parts.append({"type": "text", "text": segment})
        if i < len(text_segments) - 1 and image_queue:
            img = image_queue.pop(0)
            content_parts.append({"type": "image_url", "image_url": {"url": f"data:{img['mime_type']};base64,{img['data']}", "detail": "auto"}})
    while image_queue:
        img = image_queue.pop(0)
        content_parts.append({"type": "image_url", "image_url": {"url": f"data:{img['mime_type']};base64,{img['data']}", "detail": "auto"}})
    return content_parts

# --- Main Event Setup Function ---
def setup_message_events(bot: commands.Bot, dependencies: dict):
    request_queue = dependencies['request_queue']

    async def process_ai_request(request):
        message = request.message
        try:
            image_attachments = [att for att in (message.attachments or []) if att.content_type in ALLOWED_IMAGE_MIMES or (Path(att.filename).suffix or "").lower() in ALLOWED_IMAGE_EXTENSIONS]
            processed_images = await asyncio.gather(*[_read_image_attachment(att) for att in image_attachments])
            
            prompt_text = request.final_user_text.strip()
            user_message_content = _build_multimodal_content(prompt_text, processed_images)
            if not user_message_content: return

            api_payload = {"user_id": message.author.id, "messages": [{"role": "user", "content": user_message_content}]}

            response_message, full_response_text = None, ""
            async for chunk in api_client.stream_chat_completions(api_payload):
                full_response_text += chunk.decode('utf-8', errors='ignore')
                if response_message is None:
                    response_message = await message.channel.send(full_response_text, reference=message)
                else:
                    await response_message.edit(content=full_response_text)
            
            if not full_response_text: await message.channel.send("⚠️ The Core API returned an empty response.", reference=message)

        except Exception as e:
            logger.exception(f"Error processing request for user {message.author.id}")
            await message.channel.send(f"⚠️ An unexpected error occurred: {e}", reference=message)

    @bot.listen('on_message')
    async def on_message(message: discord.Message):
        if message.author.bot or not (isinstance(message.channel, discord.DMChannel) or bot.user in message.mentions): return
        user_text = re.sub(rf"<@!?{bot.user.id}>", "", message.content or "").strip()
        await request_queue.add_request(message, user_text)

    request_queue.set_process_callback(process_ai_request)
    logger.info("[OK] Discord message event listeners have been registered.")
