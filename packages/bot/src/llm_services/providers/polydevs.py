# providers/polydevs.py
import asyncio
import base64
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None
    _IMPORT_ERROR = "openai library not found. Please install it with 'pip install openai'"

DEFAULT_MODEL = "ryuuko-r1-mini"

# --- Helpers ---
def get_vietnam_timestamp() -> str:
    return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S GMT+7")

# --- LOGIC TẢI INSTRUCTIONS ---
INSTRUCTIONS = None
INSTRUCTIONS_LOAD_ERROR = None

def load_instructions():
    global INSTRUCTIONS_LOAD_ERROR
    try:
        config_dir = Path(__file__).resolve().parents[3] / "config"
        instruction_file = config_dir / "instructions.json"
        if not instruction_file.exists():
            error_msg = f"CRITICAL: instructions.json not found at {instruction_file.absolute()}"
            INSTRUCTIONS_LOAD_ERROR = error_msg
            return None
        with open(instruction_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict) or "vietnamese" not in data or "english" not in data:
            error_msg = "Invalid instructions.json: Phải là object chứa key 'vietnamese' và 'english'."
            INSTRUCTIONS_LOAD_ERROR = error_msg
            return None
        return data
    except Exception as e:
        error_msg = f"Unexpected error loading instructions.json: {e}"
        INSTRUCTIONS_LOAD_ERROR = error_msg
        return None

INSTRUCTIONS = load_instructions()
if INSTRUCTIONS is None:
    print(f"[POLYDEVS-PROVIDER] ⚠️ FAILED TO LOAD INSTRUCTIONS: {INSTRUCTIONS_LOAD_ERROR}")
else:
    print("[POLYDEVS-PROVIDER] ✓ Instructions loaded successfully!")

def get_instruction_by_model(model: str) -> Optional[str]:
    if INSTRUCTIONS is None: return None
    key = "english" if model and "eng" in model.lower() else "vietnamese"
    instruction_data = INSTRUCTIONS.get(key, {})
    text = instruction_data.get("system_instruction", "") if isinstance(instruction_data, dict) else str(instruction_data)
    return "\n".join(text) if isinstance(text, list) else str(text)

# ĐƠN GIẢN HÓA: Hàm này chỉ cần chuyển tiếp payload đã được chuẩn hóa
def _build_openai_messages(data: Dict, system_prompt: str) -> List[Dict[str, Any]]:
    messages = []
    timestamp_str = get_vietnam_timestamp()
    final_system_prompt = f"Current time: {timestamp_str}\n\n{system_prompt}"
    messages.append({"role": "system", "content": final_system_prompt})

    for msg in data.get("messages", []) or []:
        if not isinstance(msg, dict) or "role" not in msg or msg["role"] == "system":
            continue
        
        openai_role = "assistant" if msg["role"] in ("assistant", "model") else "user"
        # Chỉ cần chuyển tiếp content, vì nó đã được định dạng đúng ở events/messages.py
        messages.append({"role": openai_role, "content": msg["content"]})

    return messages

async def forward(request: Request, data: Dict, api_key: Optional[str]):
    if AsyncOpenAI is None:
        return JSONResponse({"ok": False, "error": "dependency_not_found", "detail": _IMPORT_ERROR}, status_code=500)
    if INSTRUCTIONS is None:
        return JSONResponse({"ok": False, "error": "configuration_error", "detail": INSTRUCTIONS_LOAD_ERROR}, status_code=500)
    key = api_key or os.getenv("POLYDEVS_API_KEY")
    if not key:
        return JSONResponse({"ok": False, "error": "api_key_not_provided"}, status_code=403)
    try:
        client = AsyncOpenAI(api_key=key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
    except Exception as e:
        return JSONResponse({"ok": False, "error": "client_initialization_failed", "detail": str(e)}, status_code=500)

    original_model = data.get("model", DEFAULT_MODEL)
    model_mapping = {
        "ryuuko-r1-vnm-pro": "gemini-2.5-pro",
        "ryuuko-r1-vnm-mini": "gemini-2.5-flash",
        "ryuuko-r1-vnm-nano": "gemini-2.5-flash",
        "ryuuko-r1-eng-pro": "gemini-2.5-pro",
        "ryuuko-r1-eng-mini": "gemini-2.5-flash",
        "ryuuko-r1-eng-nano": "gemini-2.5-flash",
    }
    final_model = model_mapping.get(original_model, original_model)

    system_prompt = get_instruction_by_model(original_model)
    if not system_prompt:
        return JSONResponse({"ok": False, "error": "instruction_error", "detail": f"Không tìm thấy instruction cho model {original_model}"}, status_code=500)

    messages = _build_openai_messages(data, system_prompt)
    if not any(m["role"] == "user" for m in messages):
        return JSONResponse({"ok": False, "error": "empty_prompt", "detail": "Không có nội dung để gửi."}, status_code=400)

    config = data.get("config", {})
    temperature = config.get("temperature")
    top_p = config.get("top_p")

    async def streamer():
        try:
            stream = await client.chat.completions.create(
                model=final_model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content.encode("utf-8")
        except Exception as e:
            error_detail = f"Upstream API error: {e}"
            yield (json.dumps({"ok": False, "error": "upstream_error", "detail": error_detail}) + "\n").encode("utf-8")

    return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")
