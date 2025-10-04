# src/core/events/messages.py
"""
Handles the on_message event and AI request processing logic.
Contains all message handling, attachment processing, and AI interaction.
"""
import re
import json
import logging
import asyncio
import base64
import mimetypes
from pathlib import Path
from typing import Set, Optional, List, Dict
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands

logger = logging.getLogger("Events.Messages")

# ---------------------------------------------------------------
# Attachment handling constants
# ---------------------------------------------------------------
FILE_MAX_BYTES = 200 * 1024  # 200 KB per file
IMAGE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB per image
MAX_CHARS_PER_FILE = 10_000
ALLOWED_TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".java", ".c", ".cpp", ".h",
    ".json", ".yaml", ".yml", ".csv", ".rs", ".go", ".rb",
    ".sh", ".html", ".css", ".ts", ".ini", ".toml",
}
ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"
}
ALLOWED_IMAGE_MIMES = {
    "image/jpeg", "image/jpg", "image/png", "image/gif",
    "image/webp", "image/bmp"
}


# ------------------------------------------------------------------
# Attachment Processing Functions
# ------------------------------------------------------------------

async def _read_image_attachment(attachment: discord.Attachment) -> Dict:
    """Process an image attachment and convert to base64."""
    entry = {
        "filename": attachment.filename,
        "type": "image",
        "data": None,
        "mime_type": None,
        "skipped": False,
        "reason": None
    }

    try:
        # Size check
        size = getattr(attachment, "size", 0) or 0
        if size > IMAGE_MAX_BYTES:
            entry["skipped"] = True
            entry["reason"] = f"image too large ({size} bytes, max {IMAGE_MAX_BYTES})"
            return entry

        # Content type check
        content_type = getattr(attachment, "content_type", "") or ""
        ext = (Path(attachment.filename).suffix or "").lower()

        if not (content_type in ALLOWED_IMAGE_MIMES or ext in ALLOWED_IMAGE_EXTENSIONS):
            entry["skipped"] = True
            entry["reason"] = f"unsupported image type ({content_type}, {ext})"
            return entry

        # Read image data
        image_data = await attachment.read()

        # Convert to base64
        base64_data = base64.b64encode(image_data).decode('utf-8')

        # Determine MIME type
        mime_type = content_type if content_type in ALLOWED_IMAGE_MIMES else mimetypes.guess_type(attachment.filename)[
            0]
        if not mime_type:
            # Fallback based on extension
            mime_mapping = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".gif": "image/gif",
                ".webp": "image/webp", ".bmp": "image/bmp"
            }
            mime_type = mime_mapping.get(ext, "image/jpeg")

        entry["data"] = base64_data
        entry["mime_type"] = mime_type
        logger.info(f"Successfully processed image: {attachment.filename} ({size} bytes, {mime_type})")

    except Exception as e:
        logger.exception(f"Error reading image attachment {attachment.filename}")
        entry["skipped"] = True
        entry["reason"] = f"read error: {e}"

    return entry


async def _read_text_attachment(attachment: discord.Attachment) -> Dict:
    """Process a text attachment."""
    entry = {"filename": attachment.filename, "type": "text", "text": "", "skipped": False, "reason": None}

    # Quick size check
    try:
        size = int(getattr(attachment, "size", 0) or 0)
    except Exception:
        size = 0

    ext = (Path(attachment.filename).suffix or "").lower()
    content_type = getattr(attachment, "content_type", "") or ""

    # Filter by content-type / extension
    if not (
            content_type.startswith("text")
            or content_type in ("application/json", "application/javascript")
            or ext in ALLOWED_TEXT_EXTENSIONS
    ):
        entry["skipped"] = True
        entry["reason"] = f"unsupported file type ({content_type!r}, {ext!r})"
        return entry

    if size and size > FILE_MAX_BYTES:
        entry["skipped"] = True
        entry["reason"] = f"file too large ({size} bytes)"
        return entry

    try:
        b = await attachment.read()
        try:
            text = b.decode("utf-8")
        except Exception:
            try:
                text = b.decode("latin-1")
            except Exception:
                text = b.decode("utf-8", errors="replace")

        # Truncate very long files
        if len(text) > MAX_CHARS_PER_FILE:
            text = text[:MAX_CHARS_PER_FILE] + "\n\n...[truncated]..."

        entry["text"] = text
    except Exception as e:
        logger.exception("Error reading attachment %s", attachment.filename)
        entry["skipped"] = True
        entry["reason"] = f"read error: {e}"

    return entry


async def _read_attachments_enhanced(attachments: List[discord.Attachment]) -> Dict:
    """Enhanced attachment processing with image support."""
    result = {
        "text_files": [],
        "images": [],
        "text_summary": "",
        "has_images": False
    }

    for att in attachments:
        ext = (Path(att.filename).suffix or "").lower()
        content_type = getattr(att, "content_type", "") or ""

        # Determine if this is an image
        if (content_type in ALLOWED_IMAGE_MIMES or ext in ALLOWED_IMAGE_EXTENSIONS):
            # Process as image
            image_entry = await _read_image_attachment(att)
            result["images"].append(image_entry)
            if not image_entry["skipped"]:
                result["has_images"] = True
        else:
            # Process as text file
            text_entry = await _read_text_attachment(att)
            result["text_files"].append(text_entry)

    # Build text summary for text files
    attach_summary = []
    files_combined = ""

    for fi in result["text_files"]:
        if fi.get("skipped"):
            attach_summary.append(f"- {fi['filename']}: SKIPPED ({fi.get('reason')})")
        else:
            attach_summary.append(f"- {fi['filename']}: included ({len(fi['text'])} chars)")
            files_combined += f"Filename: {fi['filename']}\n---\n{fi['text']}\n\n"

    # Add image summary
    for img in result["images"]:
        if img.get("skipped"):
            attach_summary.append(f"- {img['filename']}: SKIPPED ({img.get('reason')})")
        else:
            attach_summary.append(f"- {img['filename']}: image included ({img.get('mime_type')})")

    if attach_summary:
        result["text_summary"] = "\n".join(attach_summary) + "\n\n" + files_combined

    return result


# ------------------------------------------------------------------
# Message Formatting Functions
# ------------------------------------------------------------------

def convert_latex_to_discord(text: str) -> str:
    """Convert LaTeX to Discord-friendly format."""
    protected_regions = []

    def protect_region(match):
        content = match.group(0)
        placeholder = f"__PROTECTED_{len(protected_regions)}__"
        protected_regions.append(content)
        return placeholder

    patterns_to_protect = [
        r'```[\s\S]*?```',
        r'`[^`\n]*?`',
        r'#include\s*<[^>]+>',
        r'\b(?:cout|cin|std::)\b[^.\n]*?;',
        r'\bfor\s*KATEX_INLINE_OPEN[^)]*KATEX_INLINE_CLOSE\s*\{[^}]*\}',
        r'\bwhile\s*KATEX_INLINE_OPEN[^)]*KATEX_INLINE_CLOSE\s*\{[^}]*\}',
        r'\bif\s*KATEX_INLINE_OPEN[^)]*KATEX_INLINE_CLOSE\s*\{[^}]*\}',
    ]

    working_text = text
    for pattern in patterns_to_protect:
        working_text = re.sub(pattern, protect_region, working_text, flags=re.MULTILINE | re.DOTALL)

    latex_replacements = {
        r'\\cdot\b': '·', r'\\times\b': '×', r'\\div\b': '÷', r'\\pm\b': '±',
        r'\\leq\b': '≤', r'\\geq\b': '≥', r'\\neq\b': '≠', r'\\approx\b': '≈',
        r'\\alpha\b': 'α', r'\\beta\b': 'β', r'\\gamma\b': 'γ', r'\\delta\b': 'δ',
        r'\\pi\b': 'π', r'\\sigma\b': 'σ', r'\\lambda\b': 'λ', r'\\mu\b': 'μ',
        r'\\rightarrow\b': '→', r'\\to\b': '→', r'\\leftarrow\b': '←',
        r'\\sum\b': 'Σ', r'\\prod\b': 'Π', r'\\int\b': '∫',
        r'\\infty\b': '∞', r'\\emptyset\b': '∅',
    }

    for latex_pattern, replacement in latex_replacements.items():
        working_text = re.sub(latex_pattern, replacement, working_text)

    def replace_fraction(match):
        numerator = match.group(1).strip()
        denominator = match.group(2).strip()
        if len(numerator) <= 3 and len(denominator) <= 3:
            return f'{numerator}/{denominator}'
        else:
            return f'({numerator})/({denominator})'

    working_text = re.sub(r'\\frac\{([^{}]+)\}\{([^{}]+)\}', replace_fraction, working_text)

    for i, protected_content in enumerate(protected_regions):
        placeholder = f"__PROTECTED_{i}__"
        working_text = working_text.replace(placeholder, protected_content)

    return working_text


def split_message_smart(text: str, max_length: int = 2000) -> list[str]:
    """Smart message splitting."""
    if not text:
        return ["[Empty response]"]

    if len(text) <= max_length:
        return [text]

    chunks = []
    lines = text.split('\n')
    current_chunk = ""

    for line in lines:
        test_chunk = current_chunk + ('\n' if current_chunk else '') + line

        if len(test_chunk) > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                # Line too long, force split
                while len(line) > max_length:
                    chunks.append(line[:max_length])
                    line = line[max_length:]
                current_chunk = line
        else:
            current_chunk = test_chunk

    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else ["[Empty response]"]


async def send_long_message_with_reference(channel, content: str, reference_message: discord.Message,
                                           max_msg_length: int = 2000):
    """Send long message with reference."""
    try:
        formatted_content = convert_latex_to_discord(content)

        if len(formatted_content) <= max_msg_length:
            await channel.send(
                formatted_content,
                reference=reference_message,
                allowed_mentions=discord.AllowedMentions.none()
            )
            return

        chunks = split_message_smart(formatted_content, max_msg_length)

        for i, chunk in enumerate(chunks):
            try:
                if i > 0:
                    await asyncio.sleep(0.5)

                ref = reference_message if i == 0 else None
                await channel.send(
                    chunk,
                    reference=ref,
                    allowed_mentions=discord.AllowedMentions.none()
                )
            except Exception as e:
                logger.error(f"Failed to send chunk {i}: {e}")

    except Exception as e:
        logger.exception("Critical error in send_long_message_with_reference")


def get_vietnam_timestamp() -> str:
    """Get current timestamp in GMT+7 (Vietnam timezone)."""
    vietnam_tz = timezone(timedelta(hours=7))
    now = datetime.now(vietnam_tz)
    return now.strftime("[%Y-%m-%d %H:%M:%S GMT+7] ")


# ------------------------------------------------------------------
# Main Event Setup Function
# ------------------------------------------------------------------

def setup_message_events(bot: commands.Bot, dependencies: dict):
    """
    Sets up the on_message listener and AI processing logic.

    Args:
        bot: Discord bot instance
        dependencies: Dictionary containing all required dependencies
    """
    # Extract dependencies
    user_config_manager = dependencies['user_config_manager']
    request_queue = dependencies['request_queue']
    call_api = dependencies['call_api']
    memory_store = dependencies['memory_store']
    mongodb_store = dependencies.get('mongodb_store')
    authorized_users = dependencies['authorized_users']
    config = dependencies['config']

    # Helper functions
    def should_respond_default(message: discord.Message) -> bool:
        """Return True for a DM or an explicit mention of the bot."""
        if isinstance(message.channel, discord.DMChannel):
            return True
        if bot.user in message.mentions:
            return True
        return False

    async def is_authorized_user(user: discord.abc.User) -> bool:
        """Return True if user is the bot owner or in the authorized set."""
        try:
            if await bot.is_owner(user):
                return True
        except Exception:
            pass
        return getattr(user, "id", None) in authorized_users

    # ------------------------------------------------------------------
    # AI Request Processing Function
    # ------------------------------------------------------------------
    async def process_ai_request(request):
        """Process a single AI request from the queue with enhanced image support."""
        message = request.message
        final_user_text = request.final_user_text
        user_id = message.author.id

        # Safety check
        if user_config_manager is None:
            logger.error("UserConfigManager not available for request processing")
            await message.channel.send(
                "⚠️ Bot configuration not ready. Please try again later.",
                reference=message,
                allowed_mentions=discord.AllowedMentions.none()
            )
            return

        try:
            # Get user configuration
            user_model = user_config_manager.get_user_model(user_id)
            user_system_message = user_config_manager.get_user_system_message(user_id)

            # Check model access if using MongoDB
            if config.USE_MONGODB and mongodb_store:
                model_info = mongodb_store.get_model_info(user_model)
                if model_info:
                    # Check access level
                    user_config = user_config_manager.get_user_config(user_id)
                    user_level = user_config.get("access_level", 0)
                    required_level = model_info.get("access_level", 0)

                    if user_level < required_level:
                        await message.channel.send(
                            f"⛔ This model requires access level {required_level}. Your level: {user_level}",
                            reference=message,
                            allowed_mentions=discord.AllowedMentions.none()
                        )
                        return

                    # Check credits
                    cost = model_info.get("credit_cost", 0)
                    if cost > 0:
                        current_credit = user_config.get("credit", 0)
                        if current_credit < cost:
                            await message.channel.send(
                                f"⛔ Insufficient credits. This model costs {cost} credits per use. Your balance: {current_credit}",
                                reference=message,
                                allowed_mentions=discord.AllowedMentions.none()
                            )
                            return

            # Check for images and model compatibility
            attachments = list(message.attachments or [])
            attachment_data = await _read_attachments_enhanced(attachments)
            has_images = attachment_data["has_images"]

            # Build final user text with text attachments only
            combined_text = ""
            if attachment_data["text_summary"]:
                combined_text += attachment_data["text_summary"]
            if final_user_text:
                combined_text += final_user_text

            if not combined_text.strip() and not has_images:
                await message.channel.send(
                    "Please send a message with your question or attach some files.",
                    reference=message,
                    allowed_mentions=discord.AllowedMentions.none()
                )
                return

            # BUILD MESSAGE PAYLOAD (GEMINI FORMAT)
            payload_messages = []

            # Add system message
            payload_messages.append(user_system_message)

            # Add conversation history from memory
            if memory_store:
                history = memory_store.get_user_messages(user_id)
                payload_messages.extend(history)

            # Build current user message with timestamp
            final_text = f"{get_vietnam_timestamp()}{combined_text}" if memory_store else combined_text

            # CREATE MESSAGE WITH GEMINI FORMAT
            if has_images and attachment_data["images"]:
                # Multimodal message with parts
                message_parts = []

                # Add text part first
                if final_text.strip():
                    message_parts.append({"text": final_text})

                # Add image parts
                valid_image_count = 0
                for img in attachment_data["images"]:
                    if not img.get("skipped") and img.get("data"):
                        message_parts.append({
                            "inline_data": {
                                "mime_type": img.get("mime_type", "image/jpeg"),
                                "data": img["data"]  # base64 string
                            }
                        })
                        valid_image_count += 1
                        logger.info(f"Added image to payload: {img.get('filename')} ({img.get('mime_type')})")

                # Create user message with parts
                user_message = {
                    "role": "user",
                    "parts": message_parts
                }

                logger.info(f"Built multimodal message with {len(message_parts)} parts ({valid_image_count} images)")
            else:
                # Text-only message (backward compatible)
                user_message = {
                    "role": "user",
                    "content": final_text
                }
                logger.info("Built text-only message")

            payload_messages.append(user_message)

            # Debug logging
            logger.debug(f"Payload has {len(payload_messages)} messages")
            logger.debug(f"Last message type: {'multimodal (parts)' if 'parts' in user_message else 'text (content)'}")

            # CALL API
            ok, resp = await call_api.call_unified_api(
                messages=payload_messages,
                model=user_model,
                temperature=1.1,
                top_p=0.85,
                enable_tools=True,
                thinking_budget=-1
            )

            # PROCESS RESPONSE - ONLY SAVE TO MEMORY ON SUCCESS
            if ok:  # API call successful
                if resp:  # Have valid response
                    # Send response to user
                    await send_long_message_with_reference(message.channel, resp, message)

                    # Only save to memory on SUCCESS
                    if memory_store:
                        # Save user message (text only, no images to save space)
                        memory_store.add_message(user_id, {
                            "role": "user",
                            "content": combined_text  # Don't save image data
                        })
                        # Save AI response
                        memory_store.add_message(user_id, {
                            "role": "model",
                            "content": resp
                        })
                        logger.info(f"Saved conversation to memory for user {user_id}")

                    # Deduct credits if using MongoDB
                    if config.USE_MONGODB and mongodb_store and 'model_info' in locals() and model_info:
                        cost = model_info.get("credit_cost", 0)
                        if cost > 0:
                            success, remaining = mongodb_store.deduct_user_credit(user_id, cost)
                            if success:
                                logger.info(f"Deducted {cost} credits from user {user_id}. Remaining: {remaining}")
                else:
                    # ok=True but no response
                    await message.channel.send(
                        "⚠️ Received empty response from API.",
                        reference=message,
                        allowed_mentions=discord.AllowedMentions.none()
                    )
                    # Don't save to memory

            else:  # API call failed (ok=False)
                # DON'T SAVE TO MEMORY ON ERROR
                error_msg = resp or "Unknown error"

                # Log error for debug
                logger.error(f"API request failed for user {user_id}. Error: {error_msg}")

                # Parse error message if JSON
                try:
                    if isinstance(error_msg, str) and error_msg.strip().startswith('{'):
                        error_json = json.loads(error_msg)
                        if "detail" in error_json:
                            error_msg = error_json["detail"]
                        elif "error" in error_json:
                            error_msg = error_json["error"]
                except:
                    pass  # Keep original error message

                # Send error message to user
                await message.channel.send(
                    f"⚠️ Error: {str(error_msg)[:500]}",  # Limit error message length
                    reference=message,
                    allowed_mentions=discord.AllowedMentions.none()
                )
                # Don't save this conversation to memory

        except Exception as e:
            logger.exception(f"Error in request processing for user {user_id}")
            await message.channel.send(
                f"⚠️ Internal error: {str(e)[:200]}",
                reference=message,
                allowed_mentions=discord.AllowedMentions.none()
            )
            # Don't save to memory on exception

    # ------------------------------------------------------------------
    # Main on_message Event Listener
    # ------------------------------------------------------------------
    @bot.listen('on_message')
    async def on_message(message: discord.Message):
        """Main message event handler."""
        if message.author.bot:
            return

        # Safety check
        if user_config_manager is None:
            logger.error("UserConfigManager not initialized")
            return

        content = (message.content or "").strip()

        # Let command processing happen first
        ctx = await bot.get_context(message)
        if ctx.valid:
            return

        # Default trigger (DM or mention) - for AI responses
        authorized = await is_authorized_user(message.author)
        attachments = list(message.attachments or [])

        if not should_respond_default(message):
            return

        if not authorized:
            try:
                await message.channel.send("❌ You do not have permission to use this bot.",
                                           allowed_mentions=discord.AllowedMentions.none())
            except Exception:
                logger.exception("Failed to send unauthorized message")
            return

        # Check if request queue is available
        if request_queue is None:
            await message.channel.send(
                "⚠️ Bot is not ready yet. Please try again in a moment.",
                allowed_mentions=discord.AllowedMentions.none()
            )
            return

        # Build the user prompt (after stripping the bot mention)
        user_text = content
        if bot.user in message.mentions:
            user_text = re.sub(rf"<@!?{bot.user.id}>", "", content).strip()

        # Handle attachments with enhanced image support
        attachment_text = ""
        attachment_data = {"images": []}
        if attachments:
            attachment_data = await _read_attachments_enhanced(attachments)
            attachment_text = attachment_data["text_summary"]

            if attachment_data["has_images"]:
                image_count = len([img for img in attachment_data["images"] if not img.get("skipped")])
                logger.info(f"User {message.author.id} sent {image_count} valid images")

        final_user_text = (attachment_text + user_text).strip()
        if not final_user_text and not any(not img.get("skipped") for img in attachment_data.get("images", [])):
            await message.channel.send(
                "Please send a message (mention me or DM me) with your question or attach some files/images.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        # Add request to queue
        try:
            success, status_message = await request_queue.add_request(message, final_user_text)
            if not success:
                await message.channel.send(status_message, allowed_mentions=discord.AllowedMentions.none())
                return

            queue_size = request_queue._queue.qsize()
            processing_count = len(request_queue._processing_users)

            if queue_size > 1 or processing_count > 0:
                await message.channel.send(
                    status_message,
                    reference=message,
                    allowed_mentions=discord.AllowedMentions.none()
                )

        except Exception as e:
            logger.exception("Error adding request to queue")

    # Register the AI processor with the request queue
    if request_queue:
        request_queue.set_process_callback(process_ai_request)
        logger.info("AI request processor registered with queue")

    logger.info("Message event listeners have been registered")