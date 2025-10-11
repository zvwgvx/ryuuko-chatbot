# src/bot/events/messages.py
import re, json, logging, asyncio, base64, mimetypes
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
import discord
from discord.ext import commands

logger = logging.getLogger("Bot.Events.Messages")

# --- Constants ---
FILE_MAX_BYTES = 200 * 1024
IMAGE_MAX_BYTES = 10 * 1024 * 1024
MAX_CHARS_PER_FILE = 10_000
ALLOWED_TEXT_EXTENSIONS = {".txt", ".md", ".py", ".js", ".java", ".c", ".cpp", ".h", ".json", ".yaml", ".yml", ".csv",
                           ".rs", ".go", ".rb", ".sh", ".html", ".css", ".ts", ".ini", ".toml"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp", "image/bmp"}


# --- Attachment Processing Functions ---
async def _read_image_attachment(attachment: discord.Attachment) -> Dict:
    entry = {"filename": attachment.filename, "type": "image", "data": None, "mime_type": None, "skipped": False,
             "reason": None}
    try:
        size = getattr(attachment, "size", 0) or 0
        if size > IMAGE_MAX_BYTES:
            entry["skipped"], entry["reason"] = True, f"image too large ({size} bytes)"
            return entry
        content_type = getattr(attachment, "content_type", "") or ""
        ext = (Path(attachment.filename).suffix or "").lower()
        if not (content_type in ALLOWED_IMAGE_MIMES or ext in ALLOWED_IMAGE_EXTENSIONS):
            entry["skipped"], entry["reason"] = True, f"unsupported image type ({content_type}, {ext})"
            return entry
        image_data = await attachment.read()
        entry["data"] = base64.b64encode(image_data).decode('utf-8')
        entry["mime_type"] = content_type or mimetypes.guess_type(attachment.filename)[0] or "image/jpeg"
    except Exception as e:
        logger.exception(f"[ERROR] Reading image attachment {attachment.filename}")
        entry["skipped"], entry["reason"] = True, f"read error: {e}"
    return entry


async def _read_text_attachment(attachment: discord.Attachment) -> Dict:
    entry = {"filename": attachment.filename, "type": "text", "text": "", "skipped": False, "reason": None}
    try:
        size = int(getattr(attachment, "size", 0) or 0)
        ext = (Path(attachment.filename).suffix or "").lower()
        content_type = getattr(attachment, "content_type", "") or ""
        if not (content_type.startswith("text") or ext in ALLOWED_TEXT_EXTENSIONS):
            entry["skipped"], entry["reason"] = True, f"unsupported file type ({content_type!r}, {ext!r})"
            return entry
        if size and size > FILE_MAX_BYTES:
            entry["skipped"], entry["reason"] = True, f"file too large ({size} bytes)"
            return entry
        b = await attachment.read()
        entry["text"] = b.decode("utf-8", errors="replace")
        if len(entry["text"]) > MAX_CHARS_PER_FILE: entry["text"] = entry["text"][:MAX_CHARS_PER_FILE] + "\n\n...[truncated]..."
    except Exception as e:
        logger.exception("[ERROR] Reading attachment %s", attachment.filename)
        entry["skipped"], entry["reason"] = True, f"read error: {e}"
    return entry


async def _read_attachments_enhanced(attachments: List[discord.Attachment]) -> Dict:
    result = {"text_files": [], "images": [], "text_summary": "", "has_images": False}
    
    image_attachments = []
    text_attachments = []

    # SỬA LỖI: Phân loại tệp đính kèm một cách an toàn
    for att in attachments:
        ext = (Path(att.filename).suffix or "").lower()
        if att.content_type in ALLOWED_IMAGE_MIMES or ext in ALLOWED_IMAGE_EXTENSIONS:
            image_attachments.append(att)
        else:
            text_attachments.append(att)

    image_tasks = [_read_image_attachment(att) for att in image_attachments]
    text_tasks = [_read_text_attachment(att) for att in text_attachments]
    
    if image_tasks:
        result["images"] = await asyncio.gather(*image_tasks)
    if text_tasks:
        result["text_files"] = await asyncio.gather(*text_tasks)

    for img in result["images"]:
        if not img.get("skipped"): result["has_images"] = True

    attach_summary, files_combined = [], ""
    for fi in result["text_files"]:
        if fi.get("skipped"): attach_summary.append(f"- {fi['filename']}: SKIPPED ({fi.get('reason')})")
        else:
            attach_summary.append(f"- {fi['filename']}: included ({len(fi['text'])} chars)")
            files_combined += f"Filename: {fi['filename']}\n---\n{fi['text']}\n\n"
    for img in result["images"]:
        if img.get("skipped"): attach_summary.append(f"- {img['filename']}: SKIPPED ({img.get('reason')})")
        else: attach_summary.append(f"- {img['filename']}: image included ({img.get('mime_type')})")
    if attach_summary: result["text_summary"] = "\n".join(attach_summary) + "\n\n" + files_combined
    return result


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

            model_info = mongodb_store.get_model_info(user_model)
            if model_info:
                user_config = user_config_manager.get_user_config(user_id)
                user_level = user_config.get("access_level", 0)
                required_level = model_info.get("access_level", 0)
                if user_level < required_level:
                    await message.channel.send(f"⛔ Model này yêu cầu cấp độ truy cập {required_level}. Cấp độ của bạn: {user_level}", reference=message)
                    return
                cost = model_info.get("credit_cost", 0)
                if cost > 0 and user_config.get("credit", 0) < cost:
                    await message.channel.send(f"⛔ Không đủ credit. Model này tốn {cost} credit. Số dư của bạn: {user_config.get('credit', 0)}", reference=message)
                    return

            attachments = list(message.attachments or [])
            attachment_data = await _read_attachments_enhanced(attachments)
            combined_text = (attachment_data.get("text_summary", "") + request.final_user_text).strip()

            if not combined_text and not attachment_data["has_images"]: return

            payload_messages = []
            if user_system_message and user_system_message.get('content'):
                payload_messages.append(user_system_message)
            
            payload_messages.extend(memory_store.get_user_messages(user_id))

            user_content: List[Dict[str, Any]] = []
            if combined_text:
                user_content.append({"type": "text", "text": combined_text})
            
            for img in attachment_data.get("images", []):
                if not img.get("skipped") and img.get("data") and img.get("mime_type"):
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{img['mime_type']};base64,{img['data']}"}
                    })

            final_content = user_content[0]["text"] if len(user_content) == 1 and user_content[0]["type"] == "text" else user_content
            payload_messages.append({"role": "user", "content": final_content})

            ok, resp = await call_api.call_unified_api(messages=payload_messages, model=user_model)

            if ok and resp:
                await send_long_message_with_reference(message.channel, resp, message)
                memory_store.add_message(user_id, {"role": "user", "content": combined_text})
                memory_store.add_message(user_id, {"role": "assistant", "content": resp})

                if model_info and model_info.get("credit_cost", 0) > 0:
                    mongodb_store.deduct_user_credit(user_id, model_info["credit_cost"])
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
