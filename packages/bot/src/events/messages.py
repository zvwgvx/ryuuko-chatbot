# src/bot/events/messages.py
import re, json, logging, asyncio, base64, mimetypes, io
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
import discord
from discord.ext import commands
from PIL import Image

logger = logging.getLogger("Bot.Events.Messages")

# --- Constants ---
IMAGE_MAX_BYTES = 30 * 1024 * 1024 # Tăng giới hạn file ảnh
IMAGE_MAX_DIMENSION = 2048 # TĂNG GIỚI HẠN ĐỘ PHÂN GIẢI LÊN 2048PX
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp", "image/bmp"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

# --- Attachment Processing Functions ---
async def _read_image_attachment(attachment: discord.Attachment) -> Dict:
    entry = {"filename": attachment.filename, "type": "image", "data": None, "mime_type": None, "skipped": False, "reason": None}
    try:
        if attachment.size > IMAGE_MAX_BYTES:
            entry["skipped"], entry["reason"] = True, f"image too large ({attachment.size} bytes)"
            return entry
        if not (attachment.content_type in ALLOWED_IMAGE_MIMES or (Path(attachment.filename).suffix or "").lower() in ALLOWED_IMAGE_EXTENSIONS):
            entry["skipped"], entry["reason"] = True, f"unsupported image type ({attachment.content_type})"
            return entry

        image_data = await attachment.read()

        with Image.open(io.BytesIO(image_data)) as img:
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, (0, 0), img.convert('RGBA'))
                img = background

            if max(img.width, img.height) > IMAGE_MAX_DIMENSION:
                img.thumbnail((IMAGE_MAX_DIMENSION, IMAGE_MAX_DIMENSION), Image.Resampling.LANCZOS)
                logger.info(f"Resized image {attachment.filename} to fit within {IMAGE_MAX_DIMENSION}px")

            output_buffer = io.BytesIO()
            img.save(output_buffer, format='JPEG', quality=95)
            final_image_data = output_buffer.getvalue()
            entry["mime_type"] = "image/jpeg"

        entry["data"] = base64.b64encode(final_image_data).decode('utf-8')

    except Exception as e:
        logger.exception(f"[ERROR] Reading/Resizing image attachment {attachment.filename}")
        entry["skipped"], entry["reason"] = True, f"read/resize error: {e}"
    return entry

# --- Helper for Multimodal Payload ---
def _build_multimodal_content(prompt_text: str, images: List[Dict]) -> List[Dict]:
    content_parts = []
    image_queue = [img for img in images if not img.get("skipped")]
    text_segments = re.split(r'\s*\[ảnh\]\s*|\[ảnh\]', prompt_text)

    for i, segment in enumerate(text_segments):
        if segment:
            content_parts.append({"type": "text", "text": segment})
        if i < len(text_segments) - 1:
            if image_queue:
                img = image_queue.pop(0)
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{img['mime_type']};base64,{img['data']}",
                        "detail": "auto"
                    }
                })
            else:
                content_parts.append({"type": "text", "text": "\n(Missing image for placeholder)\n"})

    while image_queue:
        img = image_queue.pop(0)
        content_parts.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{img['mime_type']};base64,{img['data']}",
                "detail": "auto"
            }
        })

    if not any(part.get("text") or part.get("type") == "image_url" for part in content_parts):
        return []
    return content_parts

# --- Message Formatting Functions ---
def split_message_smart(text: str, max_length: int = 1900) -> list[str]:
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

async def send_long_message_with_reference(channel, content: str, reference_message: discord.Message):
    for i, chunk in enumerate(split_message_smart(content)):
        await channel.send(chunk, reference=reference_message if i == 0 else None, allowed_mentions=discord.AllowedMentions.none())

# --- Main Event Setup Function ---
def setup_message_events(bot: commands.Bot, dependencies: dict):
    user_config_manager = dependencies['user_config_manager']
    request_queue = dependencies['request_queue']
    call_api = dependencies['call_api']
    memory_store = dependencies['memory_store']
    mongodb_store = dependencies['mongodb_store']
    authorized_users = dependencies['authorized_users']

    async def is_authorized_user(user: discord.abc.User) -> bool:
        if await bot.is_owner(user): return True
        return getattr(user, "id", 0) in authorized_users

    async def process_ai_request(request):
        message = request.message
        user_id = message.author.id

        try:
            user_model = user_config_manager.get_user_model(user_id)
            user_system_message = user_config_manager.get_user_system_message(user_id)

            image_attachments = [att for att in (message.attachments or []) if att.content_type in ALLOWED_IMAGE_MIMES or (Path(att.filename).suffix or "").lower() in ALLOWED_IMAGE_EXTENSIONS]
            processed_images = await asyncio.gather(*[_read_image_attachment(att) for att in image_attachments])

            prompt_text = request.final_user_text.strip()
            user_message_content = _build_multimodal_content(prompt_text, processed_images)

            if not user_message_content: return

            payload_messages = []
            if user_system_message and user_system_message.get('content'):
                payload_messages.append(user_system_message)
            
            payload_messages.extend(memory_store.get_user_messages(user_id))
            
            user_message_payload = {"role": "user", "content": user_message_content}
            payload_messages.append(user_message_payload)

            ok, resp = await call_api.call_unified_api(messages=payload_messages, model=user_model)

            if ok and resp:
                try:
                    prompt_tokens = mongodb_store._count_tokens_for_message(user_message_payload)
                    completion_tokens = mongodb_store._count_tokens_for_message({"role": "assistant", "content": resp})
                    total_tokens = prompt_tokens + completion_tokens
                    logger.info(f"Token usage: Prompt={prompt_tokens}, Completion={completion_tokens}, Total={total_tokens}")
                except Exception as e:
                    logger.warning(f"Could not calculate token usage: {e}")

                await send_long_message_with_reference(message.channel, resp, message)
                
                memory_store.add_message(user_id, user_message_payload)
                memory_store.add_message(user_id, {"role": "assistant", "content": resp})

            elif not ok:
                await message.channel.send(f"⚠️ Lỗi: {str(resp)[:500]}", reference=message)

        except Exception as e:
            logger.exception(f"[ERROR] Lỗi khi xử lý request cho user {user_id}")
            await message.channel.send(f"⚠️ Lỗi nội bộ: {str(e)[:200]}", reference=message)

    @bot.listen('on_message')
    async def on_message(message: discord.Message):
        if message.author.bot: return
        ctx = await bot.get_context(message)
        if ctx.valid: return

        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mention = bot.user in message.mentions
        if not (is_dm or is_mention): return

        if not await is_authorized_user(message.author):
            await message.channel.send("❌ Bạn không có quyền sử dụng bot này.")
            return

        user_text = re.sub(rf"<@!?{bot.user.id}>", "", message.content or "").strip()
        await request_queue.add_request(message, user_text)

    request_queue.set_process_callback(process_ai_request)
    logger.info("[OK] Message event listeners have been registered")
