#!/usr/bin/env python3
# coding: utf-8
# ────────────────────────────────────────────────────────────────────────────
# Bot helper / command registry - PREFIX COMMANDS WITH IMAGE SUPPORT
# Uses MemoryStore for per‑user conversation history
# Uses UserConfigManager for per-user model and system prompt settings
# Uses MongoDB for model management
# ────────────────────────────────────────────────────────────────────────────

import re
import json
import logging
import asyncio
import time
import base64
import mimetypes
from pathlib import Path
from typing import Set, Optional, List, Dict
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands

# ────────────────────────────────────────────────────────────────────────────
# ***Relative imports for the new package structure***
from ..storage.memory import MemoryStore

logger = logging.getLogger("Functions")

# ---------------------------- module‑level state -----------------------------
_bot: Optional[commands.Bot] = None
_call_api = None
_config = None
_user_config_manager = None
_request_queue = None

# ---------------------------------------------------------------
# Persistence helpers — authorized user IDs
# ---------------------------------------------------------------
_authorized_users: Set[int] = set()

# MongoDB storage globals
_use_mongodb_auth = False
_mongodb_store = None

# ---------------------------------------------------------------
# Attachment handling constants - UPDATED FOR IMAGES
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

# ---------------------------------------------------------------
# Optional memory store
# ---------------------------------------------------------------
_memory_store: Optional[MemoryStore] = None


# ------------------------------------------------------------------
# Persistence helpers — authorized users
# ------------------------------------------------------------------

def load_authorized_from_path(path: Path) -> Set[int]:
    """Load authorized users from file (legacy mode)"""
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            arr = data.get("authorized", [])
            return set(int(x) for x in arr)
        except Exception:
            logger.exception("Failed to load authorized.json, returning empty set.")
    return set()


def save_authorized_to_path(path: Path, s: Set[int]) -> None:
    """Save authorized users to file (legacy mode)"""
    try:
        path.write_text(json.dumps({"authorized": sorted(list(s))}, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("Failed to save authorized.json")


def load_authorized_users() -> Set[int]:
    """Load authorized users from storage backend"""
    global _use_mongodb_auth, _mongodb_store

    if _use_mongodb_auth and _mongodb_store:
        return _mongodb_store.get_authorized_users()
    else:
        return load_authorized_from_path(_config.AUTHORIZED_STORE)


def add_authorized_user(user_id: int) -> bool:
    """Add user to authorized list"""
    global _authorized_users, _use_mongodb_auth, _mongodb_store

    if _use_mongodb_auth and _mongodb_store:
        success = _mongodb_store.add_authorized_user(user_id)
        if success:
            _authorized_users.add(user_id)
        return success
    else:
        _authorized_users.add(user_id)
        save_authorized_to_path(_config.AUTHORIZED_STORE, _authorized_users)
        return True


def remove_authorized_user(user_id: int) -> bool:
    """Remove user from authorized list"""
    global _authorized_users, _use_mongodb_auth, _mongodb_store

    if _use_mongodb_auth and _mongodb_store:
        success = _mongodb_store.remove_authorized_user(user_id)
        if success:
            _authorized_users.discard(user_id)
        return success
    else:
        if user_id in _authorized_users:
            _authorized_users.remove(user_id)
            save_authorized_to_path(_config.AUTHORIZED_STORE, _authorized_users)
            return True
        return False


# ------------------------------------------------------------------
# Utility helpers
# ------------------------------------------------------------------
async def is_authorized_user(user: discord.abc.User) -> bool:
    """Return True if `user` is the bot owner or in the authorized set."""
    global _bot, _authorized_users
    try:
        if await _bot.is_owner(user):
            return True
    except Exception:
        pass
    return getattr(user, "id", None) in _authorized_users


def _extract_user_id_from_str(s: str) -> Optional[int]:
    m = re.search(r"(\d{17,20})", s)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    if s.isdigit():
        try:
            return int(s)
        except Exception:
            return None
    return None


def should_respond_default(message: discord.Message) -> bool:
    """Return True for a DM or an explicit mention of the bot."""
    if isinstance(message.channel, discord.DMChannel):
        return True
    if _bot.user in message.mentions:
        return True
    return False


# ------------------------------------------------------------------
# Enhanced Attachment helpers - WITH IMAGE SUPPORT
# ------------------------------------------------------------------

async def _read_image_attachment(attachment: discord.Attachment) -> Dict:
    """Process an image attachment and convert to base64"""
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
    """Process a text attachment"""
    entry = {"filename": attachment.filename, "type": "text", "text": "", "skipped": False, "reason": None}

    # quick size check
    try:
        size = int(getattr(attachment, "size", 0) or 0)
    except Exception:
        size = 0

    ext = (Path(attachment.filename).suffix or "").lower()
    content_type = getattr(attachment, "content_type", "") or ""

    # filter by content‑type / extension
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

        # truncate very long files
        if len(text) > MAX_CHARS_PER_FILE:
            text = text[:MAX_CHARS_PER_FILE] + "\n\n...[truncated]..."

        entry["text"] = text
        logger.info(f"Successfully processed text file: {attachment.filename} ({size} bytes)")
    except Exception as e:
        logger.exception("Error reading attachment %s", attachment.filename)
        entry["skipped"] = True
        entry["reason"] = f"read error: {e}"

    return entry


async def _read_attachments_enhanced(attachments: List[discord.Attachment]) -> Dict:
    """Enhanced attachment processing with image support - reads and stores base64 data"""
    result = {
        "text_files": [],
        "images": [],
        "text_summary": "",
        "has_images": False,
        "has_valid_images": False,
        "has_text_files": False
    }

    for att in attachments:
        ext = (Path(att.filename).suffix or "").lower()
        content_type = getattr(att, "content_type", "") or ""

        # Determine if this is an image
        if (content_type in ALLOWED_IMAGE_MIMES or ext in ALLOWED_IMAGE_EXTENSIONS):
            # Process as image
            image_entry = await _read_image_attachment(att)
            result["images"].append(image_entry)
            result["has_images"] = True
            if not image_entry["skipped"]:
                result["has_valid_images"] = True
        else:
            # Process as text file
            text_entry = await _read_text_attachment(att)
            result["text_files"].append(text_entry)
            if not text_entry["skipped"]:
                result["has_text_files"] = True

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
# Message formatting helpers
# ------------------------------------------------------------------

def convert_latex_to_discord(text: str) -> str:
    """Convert LaTeX to Discord-friendly format"""
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
    """Smart message splitting"""
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
    """Send long message with reference"""
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


# ------------------------------------------------------------------
# AI Request Processing Function
# ------------------------------------------------------------------

def get_vietnam_timestamp() -> str:
    """Get current timestamp in GMT+7 (Vietnam timezone)"""
    vietnam_tz = timezone(timedelta(hours=7))
    now = datetime.now(vietnam_tz)
    formatted_time = now.strftime("%A, %B %d, %Y - %H:%M:%S")
    return f"Current time: {formatted_time} (GMT+7) : "


async def process_ai_request(request):
    """Process a single AI request from the queue with enhanced image support"""
    message = request.message
    final_user_text = request.final_user_text
    user_id = message.author.id

    # Get attachment_data from request (already processed and stored)
    attachment_data = getattr(request, 'attachment_data', None)

    if attachment_data is None:
        # Fallback: empty data structure
        logger.warning("⚠️ No attachment_data in request, using empty structure")
        attachment_data = {
            "images": [],
            "text_files": [],
            "has_valid_images": False,
            "has_text_files": False,
            "text_summary": ""
        }
    else:
        # Log that we're using stored data
        if attachment_data.get("has_valid_images"):
            image_count = len([img for img in attachment_data["images"] if not img.get("skipped")])
            logger.info(f"✅ Using {image_count} pre-loaded image(s) from queue for user {user_id}")

    # Safety check
    if _user_config_manager is None:
        logger.error("UserConfigManager not available for request processing")
        await message.channel.send(
            "⚠️ Bot configuration not ready. Please try again later.",
            reference=message,
            allowed_mentions=discord.AllowedMentions.none()
        )
        return

    try:
        # Get user configuration
        user_model = _user_config_manager.get_user_model(user_id)
        user_system_message = _user_config_manager.get_user_system_message(user_id)

        # Check model access if using MongoDB
        if _use_mongodb_auth and _mongodb_store:
            model_info = _mongodb_store.get_model_info(user_model)
            if model_info:
                # Check access level
                user_config = _user_config_manager.get_user_config(user_id)
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

        # Use attachment_data from request (already processed)
        has_images = attachment_data["has_valid_images"]
        has_text_files = attachment_data["has_text_files"]

        # Build text content (text files + user text)
        text_files_content = ""
        for fi in attachment_data.get("text_files", []):
            if not fi.get("skipped"):
                text_files_content += f"Filename: {fi['filename']}\n---\n{fi['text']}\n\n"

        # Clean user text - remove the attachment summary lines
        user_text_clean = final_user_text
        if attachment_data["text_summary"]:
            # Remove summary lines from final_user_text
            for line in attachment_data["text_summary"].split('\n'):
                if line.strip():
                    user_text_clean = user_text_clean.replace(line, '')
        user_text_clean = user_text_clean.strip()

        combined_text = text_files_content + user_text_clean

        if not combined_text.strip() and not has_images:
            await message.channel.send(
                "Please send a message with your question or attach some files/images.",
                reference=message,
                allowed_mentions=discord.AllowedMentions.none()
            )
            return

        # Build message payload
        payload_messages = [user_system_message]
        if _memory_store:
            payload_messages.extend(_memory_store.get_user_messages(user_id))

        # Create the user message content
        timestamp_prefix = get_vietnam_timestamp() if _memory_store else ""
        final_text_content = f"{timestamp_prefix}{combined_text}" if combined_text.strip() else ""

        # Build the user message with proper format for images
        if has_images:
            # Build content array for vision models
            content_parts = []

            # Add text content first
            if final_text_content.strip():
                content_parts.append({
                    "type": "text",
                    "text": final_text_content
                })

            # Add images from stored attachment_data
            valid_images_added = 0
            for img in attachment_data["images"]:
                if not img.get("skipped") and img.get("data"):
                    # Use pre-loaded base64 data
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{img['mime_type']};base64,{img['data']}"
                        }
                    })
                    valid_images_added += 1
                    logger.info(f"✅ Added pre-loaded image to API payload: {img['filename']} ({img['mime_type']})")

            if not content_parts:
                await message.channel.send(
                    "No valid content to process. Please check your attachments.",
                    reference=message,
                    allowed_mentions=discord.AllowedMentions.none()
                )
                return

            user_message = {
                "role": "user",
                "content": content_parts
            }

            logger.info(f"🖼️ Built vision message with {valid_images_added} image(s) for user {user_id}")

            # DEBUG: Log structure
            for i, part in enumerate(content_parts):
                if part["type"] == "text":
                    logger.debug(f"  Part {i}: text ({len(part['text'])} chars)")
                elif part["type"] == "image_url":
                    url = part["image_url"]["url"]
                    mime = url.split(";")[0].replace("data:", "")
                    b64_len = len(url.split(",", 1)[1]) if "," in url else 0
                    logger.debug(f"  Part {i}: image ({mime}, {b64_len} base64 chars)")

        else:
            # Text-only message
            if not final_text_content.strip():
                await message.channel.send(
                    "Please provide some text content.",
                    reference=message,
                    allowed_mentions=discord.AllowedMentions.none()
                )
                return

            user_message = {
                "role": "user",
                "content": final_text_content
            }

            logger.info(f"📝 Built text-only message for user {user_id}")

        payload_messages.append(user_message)

        # Log payload structure
        logger.debug(f"📦 Message payload for user {user_id}: {len(payload_messages)} messages, "
                     f"last message type: {'vision' if has_images else 'text'}")

        # ✅ Call API directly (async function, no executor needed)
        ok, resp = await _call_api(
            messages=payload_messages,
            model=user_model
        )

        if ok and resp:
            await send_long_message_with_reference(message.channel, resp, message)

            # Add to memory (simplified version)
            if _memory_store:
                memory_user_content = combined_text if combined_text.strip() else "[Image(s) sent]"
                if has_images:
                    image_count = len([img for img in attachment_data["images"] if not img.get("skipped")])
                    if combined_text.strip():
                        memory_user_content = f"{combined_text}\n[{image_count} image(s) attached]"
                    else:
                        memory_user_content = f"[{image_count} image(s) sent]"

                _memory_store.add_message(user_id, {"role": "user", "content": memory_user_content})
                _memory_store.add_message(user_id, {"role": "model", "content": resp})

            # Deduct credits
            if _use_mongodb_auth and _mongodb_store and 'model_info' in locals() and model_info:
                cost = model_info.get("credit_cost", 0)
                if cost > 0:
                    success, remaining = _mongodb_store.deduct_user_credit(user_id, cost)
                    if success:
                        logger.info(f"Deducted {cost} credits from user {user_id}. Remaining: {remaining}")

            logger.info(f"✅ Successfully processed request for user {user_id} with model {user_model}")

        else:
            error_msg = resp or "Unknown error"
            await message.channel.send(
                f"⚠️ Error: {error_msg}",
                reference=message,
                allowed_mentions=discord.AllowedMentions.none()
            )
            logger.error(f"API call failed for user {user_id}: {error_msg}")

    except Exception as e:
        logger.exception(f"Error in request processing for user {user_id}")
        await message.channel.send(
            f"⚠️ Internal error: {e}",
            reference=message,
            allowed_mentions=discord.AllowedMentions.none()
        )


# ------------------------------------------------------------------
# PREFIX COMMANDS - Basic Commands
# ------------------------------------------------------------------

@commands.command(name="help")
async def help_command(ctx):
    """Show available commands"""
    is_owner = False
    try:
        is_owner = await _bot.is_owner(ctx.author)
    except Exception:
        pass

    lines = [
        "**Available commands:**",
        "`.ping` – Check bot responsiveness",
        "",
        "**Configuration commands (authorized users):**",
        "`.model <model>` – Set your preferred AI model",
        "`.sysprompt <prompt>` – Set your system prompt",
        "`.profile [user]` – Show user configuration",
        "`.showprompt [user]` – View system prompt",
        "`.models` – Show all supported models",
        "`.clearmemory [user]` – Clear conversation history",
        "",
        "**File & Image Support:**",
        "• Send images directly (JPG, PNG, GIF, WebP, BMP)",
        "• Attach text files (TXT, MD, PY, JSON, etc.)",
    ]

    if is_owner:
        lines += [
            "",
            "**Owner‑only commands:**",
            "`.auth <user>` – Add a user to authorized list",
            "`.deauth <user>` – Remove user from authorized list",
            "`.auths` – List authorized users",
            "`.memory [user]` – View conversation history",
            "",
            "**Model management (owner only):**",
            "`.addmodel <name> <cost> <level>` – Add a new model",
            "`.removemodel <name>` – Remove a model",
            "`.editmodel <name> <cost> <level>` – Edit model settings",
            "",
            "**Credit management (owner only):**",
            "`.addcredit <user> <amount>` – Add credits to user",
            "`.deductcredit <user> <amount>` – Deduct credits from user",
            "`.setcredit <user> <amount>` – Set user's credit balance",
            "`.setlevel <user> <level>` – Set user access level (0-3)"
        ]

    await ctx.send("\n".join(lines))


@commands.command(name="ping")
async def ping_command(ctx):
    """Ping command"""
    start_time = time.perf_counter()
    msg = await ctx.send("Pinging...")
    end_time = time.perf_counter()

    latency_ms = round((end_time - start_time) * 1000)
    ws_latency = round(_bot.latency * 1000) if _bot.latency else "N/A"

    content = f"Pong! \nResponse: {latency_ms} ms\nWebSocket: {ws_latency} ms"
    await msg.edit(content=content)


# ------------------------------------------------------------------
# PREFIX COMMANDS - User Configuration Commands
# ------------------------------------------------------------------

@commands.command(name="model")
async def set_model_command(ctx, *, model: str):
    """Set user model"""
    if not await is_authorized_user(ctx.author):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    if _user_config_manager is None:
        await ctx.send("❌ Bot configuration not ready.")
        return

    available, error = _call_api.is_model_available(model.strip())
    if not available:
        await ctx.send(f"❌ {error}")
        return

    success, message = _user_config_manager.set_user_model(ctx.author.id, model.strip())
    await ctx.send(f"✅ {message}")


@commands.command(name="sysprompt")
async def set_sys_prompt_command(ctx, *, prompt: str):
    """Set user system prompt"""
    if not await is_authorized_user(ctx.author):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    if _user_config_manager is None:
        await ctx.send("❌ Bot configuration not ready.")
        return

    success, message = _user_config_manager.set_user_system_prompt(ctx.author.id, prompt)
    await ctx.send(f"✅ {message}")


@commands.command(name="profile")
async def show_profile_command(ctx, member: discord.Member = None):
    """Show user profile"""
    if _user_config_manager is None:
        await ctx.send("❌ Bot configuration not ready.")
        return

    target_user = member or ctx.author

    if target_user != ctx.author:
        try:
            is_owner = await _bot.is_owner(ctx.author)
        except Exception:
            is_owner = False

        if not is_owner:
            await ctx.send("❌ You can only view your own profile.")
            return

    # Gather config for the target user
    user_config = _user_config_manager.get_user_config(target_user.id)

    # Get additional info
    model = user_config["model"]
    credit = user_config.get("credit", 0)
    access_level = user_config.get("access_level", 0)

    # Level description
    level_desc = {
        0: "Basic (Level 0)",
        1: "Advanced (Level 1)",
        2: "Premium (Level 2)",
        3: "Ultimate (Level 3)"
    }.get(access_level, f"Unknown (Level {access_level})")

    # Build profile display
    lines = [
        f"**Profile for {target_user}:**",
        f"**Current Model**: {model}",
        f"**Credit Balance**: {credit}",
        f"**Access Level**: {level_desc}",
        "",
        "Use `.showprompt` to view system prompt."
    ]

    await ctx.send("\n".join(lines))


@commands.command(name="showprompt")
async def show_sys_prompt_command(ctx, member: discord.Member = None):
    """Show user system prompt"""
    if _user_config_manager is None:
        await ctx.send("❌ Bot configuration not ready.")
        return

    target_user = member or ctx.author

    # Check if viewer is owner when viewing other's prompt
    if target_user != ctx.author:
        try:
            is_owner = await _bot.is_owner(ctx.author)
        except Exception:
            is_owner = False

        if not is_owner:
            await ctx.send("❌ Only the bot owner can view other users' system prompts.")
            return

    # Get system prompt
    user_config = _user_config_manager.get_user_config(target_user.id)
    prompt = user_config["system_prompt"]

    # Format display
    lines = [
        f"**System Prompt for {target_user}:**",
        "```",
        prompt,
        "```"
    ]

    await ctx.send("\n".join(lines))


@commands.command(name="models")
async def show_models_command(ctx):
    """Show available models"""
    if _user_config_manager is None:
        await ctx.send("❌ Bot configuration not ready.")
        return

    if _use_mongodb_auth and _mongodb_store:
        # Get models from MongoDB
        all_models = _mongodb_store.list_all_models()

        if all_models:
            models_info = []

            # Sort all models
            sorted_models = sorted(
                all_models,
                key=lambda x: (-x.get("access_level", 0), -x.get("credit_cost", 0), x.get("model_name", ""))
            )

            current_level = None
            for model in sorted_models:
                model_name = model.get("model_name", "Unknown")
                credit_cost = model.get("credit_cost", 0)
                access_level = model.get("access_level", 0)

                level_names = {0: "Basic", 1: "Advanced", 2: "Premium", 3: "Ultimate"}
                level_name = level_names.get(access_level, f"Level {access_level}")

                if current_level != access_level:
                    models_info.append(f"\n**{level_name} Models:**")
                    current_level = access_level

                models_info.append(f"• `{model_name}` - {credit_cost} credits")

            lines = [
                "**Available AI Models:**",
                *models_info,
                "",
                "Use `.model <model_name>` to change your model."
            ]
        else:
            lines = ["No models found."]
    else:
        # Fallback for file mode
        supported_models = _user_config_manager.get_supported_models()
        models_list = []
        for model in sorted(supported_models):
            models_list.append(f"• `{model}`")

        lines = [
            "**Supported AI Models:**",
            "\n".join(models_list),
            "",
            "Use `.model <model_name>` to change your model."
        ]

    await ctx.send("\n".join(lines))


@commands.command(name="clearmemory")
async def clearmemory_command(ctx, member: discord.Member = None):
    """Clear conversation history"""
    target_user = member or ctx.author

    # Check if trying to clear someone else's memory
    if target_user != ctx.author:
        try:
            is_owner = await _bot.is_owner(ctx.author)
        except Exception:
            is_owner = False

        if not is_owner:
            await ctx.send("❌ You can only clear your own memory.")
            return

    # Check if user is authorized (for clearing their own memory)
    if target_user == ctx.author and not await is_authorized_user(ctx.author):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    if _memory_store is None:
        await ctx.send("❌ Memory feature not initialized.")
        return

    _memory_store.clear_user(target_user.id)

    if target_user == ctx.author:
        await ctx.send("✅ Cleared your conversation memory.")
    else:
        await ctx.send(f"✅ Cleared memory for {target_user}.")


# ------------------------------------------------------------------
# PREFIX COMMANDS - Owner-only User Management
# ------------------------------------------------------------------

@commands.command(name="auth")
@commands.is_owner()
async def auth_command(ctx, member: discord.Member):
    """Add user to authorized list"""
    uid = member.id
    if uid in _authorized_users:
        await ctx.send(f"❌ User {member} is already authorized.")
        return

    success = add_authorized_user(uid)
    if success:
        await ctx.send(f"✅ Added {member} to authorized list.")
    else:
        await ctx.send(f"❌ Failed to add {member} to authorized list.")


@commands.command(name="deauth")
@commands.is_owner()
async def deauth_command(ctx, member: discord.Member):
    """Remove user from authorized list"""
    uid = member.id
    if uid not in _authorized_users:
        await ctx.send(f"❌ User {member} is not in the authorized list.")
        return

    success = remove_authorized_user(uid)
    if success:
        await ctx.send(f"✅ Removed {member} from authorized list.")
    else:
        await ctx.send(f"❌ Failed to remove {member} from authorized list.")


@commands.command(name="auths")
@commands.is_owner()
async def show_auth_command(ctx):
    """Show authorized users"""
    if not _authorized_users:
        await ctx.send("Authorized users list is empty.")
        return

    body = "\n".join(str(x) for x in sorted(_authorized_users))
    if len(body) > 1900:
        # Create file if too long
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Authorized Users:\n")
            f.write(body)
            temp_path = f.name
        try:
            await ctx.send(
                "Too long data, sending file.",
                file=discord.File(temp_path, filename="authorized_users.txt")
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)
    else:
        await ctx.send(f"**Authorized users:**\n{body}")


@commands.command(name="memory")
@commands.is_owner()
async def memory_command(ctx, member: discord.Member = None):
    """View conversation history"""
    target = member or ctx.author
    if _memory_store is None:
        await ctx.send("❌ Memory feature not initialized.")
        return

    mem = _memory_store.get_user_messages(target.id)
    if not mem:
        await ctx.send(f"No memory for {target}.")
        return

    lines = []
    for i, msg in enumerate(mem[-10:], start=1):
        content = msg["content"]
        preview = (content[:120] + "…") if len(content) > 120 else content
        lines.append(f"{i:02d}. **{msg['role']}**: {preview}")

    await ctx.send("\n".join(lines))


# ------------------------------------------------------------------
# Model Management Commands (Owner only)
# ------------------------------------------------------------------

@commands.command(name="addmodel")
@commands.is_owner()
async def add_model_command(ctx, model_name: str, credit_cost: int, access_level: int):
    """Add a new model (owner only)"""

    if credit_cost < 0:
        await ctx.send("❌ Credit cost must be positive.")
        return

    if access_level not in [0, 1, 2, 3]:
        await ctx.send("❌ Access level must be 0-3 (0=Basic, 1=Advanced, 2=Premium, 3=Ultimate)")
        return

    if not _config.USE_MONGODB:
        await ctx.send("❌ Model management requires MongoDB mode to be enabled.")
        return

    if not _mongodb_store:
        await ctx.send("❌ MongoDB not available.")
        return

    try:
        success, message = _mongodb_store.add_supported_model(model_name, credit_cost, access_level)
        if success:
            await ctx.send(f"✅ {message}")
        else:
            await ctx.send(f"❌ {message}")
    except Exception as e:
        logger.exception(f"Error adding model: {e}")
        await ctx.send(f"❌ Error adding model: {str(e)[:100]}")


@commands.command(name="removemodel")
@commands.is_owner()
async def remove_model_command(ctx, model_name: str):
    """Remove a model (owner only)"""

    if not _config.USE_MONGODB:
        await ctx.send("❌ Model management requires MongoDB mode to be enabled.")
        return

    if not _mongodb_store:
        await ctx.send("❌ MongoDB not available.")
        return

    try:
        success, message = _mongodb_store.remove_supported_model(model_name)
        if success:
            await ctx.send(f"✅ {message}")
        else:
            await ctx.send(f"❌ {message}")
    except Exception as e:
        logger.exception(f"Error removing model: {e}")
        await ctx.send(f"❌ Error removing model: {str(e)[:100]}")


@commands.command(name="editmodel")
@commands.is_owner()
async def edit_model_command(ctx, model_name: str, credit_cost: int, access_level: int):
    """Edit a model (owner only)"""

    if credit_cost < 0:
        await ctx.send("❌ Credit cost must be positive.")
        return

    if access_level not in [0, 1, 2, 3]:
        await ctx.send("❌ Access level must be 0-3 (0=Basic, 1=Advanced, 2=Premium, 3=Ultimate)")
        return

    if not _config.USE_MONGODB:
        await ctx.send("❌ Model management requires MongoDB mode to be enabled.")
        return

    if not _mongodb_store:
        await ctx.send("❌ MongoDB not available.")
        return

    try:
        success, message = _mongodb_store.edit_supported_model(model_name, credit_cost, access_level)
        if success:
            await ctx.send(f"✅ {message}")
        else:
            await ctx.send(f"❌ {message}")
    except Exception as e:
        logger.exception(f"Error editing model: {e}")
        await ctx.send(f"❌ Error editing model: {str(e)[:100]}")


# ------------------------------------------------------------------
# Credit Management Commands (Owner only)
# ------------------------------------------------------------------

@commands.command(name="addcredit")
@commands.is_owner()
async def add_credit_command(ctx, member: discord.Member, amount: int):
    """Add credits to user (owner only)"""

    if amount <= 0:
        await ctx.send("❌ Amount must be positive.")
        return

    if not _use_mongodb_auth:
        await ctx.send("❌ Credit system requires MongoDB mode.")
        return

    if not _mongodb_store:
        await ctx.send("❌ MongoDB not available.")
        return

    try:
        success, new_balance = _mongodb_store.add_user_credit(member.id, amount)
        if success:
            await ctx.send(f"✅ Added {amount} credits to {member}'s balance. New balance: {new_balance}")
        else:
            await ctx.send("❌ Failed to add credits")
    except Exception as e:
        logger.exception(f"Error adding credits: {e}")
        await ctx.send(f"❌ Error adding credits: {str(e)[:100]}")


@commands.command(name="deductcredit")
@commands.is_owner()
async def deduct_credit_command(ctx, member: discord.Member, amount: int):
    """Deduct credits from user (owner only)"""

    if amount <= 0:
        await ctx.send("❌ Amount must be positive.")
        return

    if not _use_mongodb_auth:
        await ctx.send("❌ Credit system requires MongoDB mode.")
        return

    if not _mongodb_store:
        await ctx.send("❌ MongoDB not available.")
        return

    try:
        success, new_balance = _mongodb_store.deduct_user_credit(member.id, amount)
        if success:
            await ctx.send(f"✅ Deducted {amount} credits from {member}'s balance. New balance: {new_balance}")
        else:
            await ctx.send("❌ Failed to deduct credits (insufficient balance or error)")
    except Exception as e:
        logger.exception(f"Error deducting credits: {e}")
        await ctx.send(f"❌ Error deducting credits: {str(e)[:100]}")


@commands.command(name="setcredit")
@commands.is_owner()
async def set_credit_command(ctx, member: discord.Member, amount: int):
    """Set user's credit balance (owner only)"""

    if amount < 0:
        await ctx.send("❌ Amount must be non-negative.")
        return

    if not _use_mongodb_auth:
        await ctx.send("❌ Credit system requires MongoDB mode.")
        return

    if not _mongodb_store:
        await ctx.send("❌ MongoDB not available.")
        return

    try:
        success = _mongodb_store.set_user_credit(member.id, amount)
        if success:
            await ctx.send(f"✅ Set {member}'s credit balance to {amount}")
        else:
            await ctx.send("❌ Failed to set credits")
    except Exception as e:
        logger.exception(f"Error setting credits: {e}")
        await ctx.send(f"❌ Error setting credits: {str(e)[:100]}")


@commands.command(name="setlevel")
@commands.is_owner()
async def set_level_command(ctx, member: discord.Member, level: int):
    """Set user access level (owner only)"""

    if level not in [0, 1, 2, 3]:
        await ctx.send("❌ Level must be 0-3 (0=Basic, 1=Advanced, 2=Premium, 3=Ultimate)")
        return

    if not _use_mongodb_auth:
        await ctx.send("❌ User levels require MongoDB mode.")
        return

    if not _mongodb_store:
        await ctx.send("❌ MongoDB not available.")
        return

    try:
        success = _mongodb_store.set_user_level(member.id, level)
        if success:
            level_names = {0: "Basic", 1: "Advanced", 2: "Premium", 3: "Ultimate"}
            await ctx.send(f"✅ Set {member}'s level to {level_names[level]} (Level {level})")
        else:
            await ctx.send("❌ Failed to set user level")
    except Exception as e:
        logger.exception(f"Error setting level: {e}")
        await ctx.send(f"❌ Error setting level: {str(e)[:100]}")


# ------------------------------------------------------------------
# on_message listener - ✅ FIXED: Pass attachment_data to queue
# ------------------------------------------------------------------
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if _user_config_manager is None:
        logger.error("UserConfigManager not initialized")
        return

    content = (message.content or "").strip()

    # Let command processing happen first
    ctx = await _bot.get_context(message)
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

    if _request_queue is None:
        await message.channel.send(
            "⚠️ Bot is not ready yet. Please try again in a moment.",
            allowed_mentions=discord.AllowedMentions.none()
        )
        return

    # Build the user prompt (after stripping the bot mention)
    user_text = content
    if _bot.user in message.mentions:
        user_text = re.sub(rf"<@!?{_bot.user.id}>", "", content).strip()

    # ✅ FIX: Read attachments ONCE and keep the base64 data
    attachment_data = {
        "images": [],
        "text_files": [],
        "has_valid_images": False,
        "has_text_files": False,
        "text_summary": ""
    }

    if attachments:
        logger.info(f"📎 Processing {len(attachments)} attachment(s) for user {message.author.id}")
        attachment_data = await _read_attachments_enhanced(attachments)

        if attachment_data["has_valid_images"]:
            image_count = len([img for img in attachment_data["images"] if not img.get("skipped")])
            logger.info(f"✅ Loaded {image_count} valid image(s) into memory")

            # DEBUG: Log base64 sizes
            for img in attachment_data["images"]:
                if not img.get("skipped"):
                    b64_len = len(img.get("data", ""))
                    logger.debug(f"  Image '{img['filename']}': {b64_len} base64 chars (~{b64_len * 3 // 4} bytes)")

    # Build text for queue display
    attachment_text = attachment_data["text_summary"]
    final_user_text = (attachment_text + user_text).strip()

    # Check if there's any valid content
    has_valid_content = (
            final_user_text.strip() or
            attachment_data.get("has_valid_images", False)
    )

    if not has_valid_content:
        await message.channel.send(
            "Please send a message (mention me or DM me) with your question or attach some files/images.",
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return

    # ✅ FIX: Pass attachment_data to queue (with base64 image data)
    try:
        success, status_message = await _request_queue.add_request(
            message,
            final_user_text,
            attachment_data  # ✅ This contains the base64 images!
        )

        if not success:
            await message.channel.send(status_message, allowed_mentions=discord.AllowedMentions.none())
            return

        queue_size = _request_queue._queue.qsize()
        processing_count = len(_request_queue._processing_users)

        if queue_size > 1 or processing_count > 0:
            await message.channel.send(
                status_message,
                reference=message,
                allowed_mentions=discord.AllowedMentions.none()
            )

    except Exception as e:
        logger.exception("Error adding request to queue")


# ------------------------------------------------------------------
# Setup function
# ------------------------------------------------------------------
def setup(bot: commands.Bot, call_api_module, config_module):
    global _bot, _call_api, _config, _authorized_users, _memory_store, _user_config_manager, _request_queue
    global _use_mongodb_auth, _mongodb_store

    logger.info("🔧 Starting functions.py setup...")

    _bot = bot
    _call_api = call_api_module
    _config = config_module

    # 1. Initialize storage backend FIRST
    try:
        _config.init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"❌ Storage init failed: {e}")

    # 2. Setup MongoDB globals AFTER storage init
    _use_mongodb_auth = _config.USE_MONGODB
    if _use_mongodb_auth:
        try:
            from src.storage.database import get_mongodb_store
            _mongodb_store = get_mongodb_store()
            logger.info("Using MongoDB for data storage")
        except Exception as e:
            logger.error(f"❌ MongoDB init failed: {e}")
            _mongodb_store = None
            _use_mongodb_auth = False
    else:
        _mongodb_store = None
        logger.info("Using file-based storage (legacy mode)")

    # 3. Initialize managers AFTER storage is ready
    try:
        from src.config import get_user_config_manager
        from src.utils import get_request_queue

        _user_config_manager = get_user_config_manager()
        _request_queue = get_request_queue()
        logger.info("Managers initialized")
    except Exception as e:
        logger.error(f"❌ Managers init failed: {e}")
        _user_config_manager = None
        _request_queue = None

    # 4. Setup queue ONLY if it exists
    if _request_queue is not None:
        try:
            _request_queue.set_bot(bot)
            _request_queue.set_process_callback(process_ai_request)
            logger.info("Request queue setup")
        except Exception as e:
            logger.error(f"❌ Request queue setup failed: {e}")
    else:
        logger.warning("⚠️  Request queue not available")

    # 5. Load authorized users
    try:
        _authorized_users = load_authorized_users()
        logger.info(f"Loaded {len(_authorized_users)} authorized users")
    except Exception as e:
        logger.error(f"❌ Failed to load authorized users: {e}")
        _authorized_users = set()

    # 6. Initialize memory store
    try:
        from src.storage import MemoryStore
        _memory_store = MemoryStore()
        logger.info("Memory store initialized")
    except Exception as e:
        logger.error(f"❌ Memory store init failed: {e}")
        _memory_store = None

    # Register prefix commands
    try:
        # Basic commands
        bot.add_command(help_command)
        bot.add_command(ping_command)

        # User commands
        bot.add_command(set_model_command)
        bot.add_command(set_sys_prompt_command)
        bot.add_command(show_profile_command)
        bot.add_command(show_sys_prompt_command)
        bot.add_command(show_models_command)
        bot.add_command(clearmemory_command)

        # Owner commands
        bot.add_command(auth_command)
        bot.add_command(deauth_command)
        bot.add_command(show_auth_command)
        bot.add_command(memory_command)

        # Model management commands
        bot.add_command(add_model_command)
        bot.add_command(remove_model_command)
        bot.add_command(edit_model_command)

        # Credit management commands
        bot.add_command(add_credit_command)
        bot.add_command(deduct_credit_command)
        bot.add_command(set_credit_command)
        bot.add_command(set_level_command)

        logger.info("All prefix commands registered")
    except Exception as e:
        logger.error(f"❌ Failed to register commands: {e}")

    # Register on_message listener
    try:
        bot.add_listener(on_message, "on_message")
        logger.info("on_message listener registered")
    except Exception as e:
        logger.error(f"❌ Failed to register on_message listener: {e}")

    logger.info("🎉  Functions module setup completed!")