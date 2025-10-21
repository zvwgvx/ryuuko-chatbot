# providers/aistudio.py
import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None
    _IMPORT_ERROR = "openai library not found. Please install it with 'pip install openai'"

DEFAULT_MODEL = "gemini-2.5-flash"

# --- Helpers ---
def get_vietnam_timestamp() -> str:
    return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S GMT+7")

# --- SỬA LỖI: Tích hợp timestamp một cách tự nhiên ---
def _build_openai_messages(data: Dict) -> List[Dict[str, Any]]:
    messages = []
    
    timestamp_str = get_vietnam_timestamp()
    # Bắt đầu prompt với thông tin thời gian
    system_content = f"The current date and time is {timestamp_str}."
    
    user_system_instructions = data.get("system_instruction", [])
    if isinstance(user_system_instructions, list) and user_system_instructions:
        full_user_prompt = "\n".join(filter(None, [str(s).strip() for s in user_system_instructions]))
        if full_user_prompt:
            # Nối phần còn lại của system prompt vào
            system_content += f" {full_user_prompt}"
            
    messages.append({"role": "system", "content": system_content})

    for msg in data.get("messages", []) or []:
        if not isinstance(msg, dict) or "role" not in msg or msg["role"] == "system":
            continue
        messages.append({"role": msg["role"], "content": msg["content"]})

    return messages


async def forward(request: Request, data: Dict, api_key: Optional[str]):
    if AsyncOpenAI is None: return JSONResponse({"ok": False, "error": "dependency_not_found", "detail": _IMPORT_ERROR}, status_code=500)
    
    key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("AISTUDIO_API_KEY")
    if not key: return JSONResponse({"ok": False, "error": "api_key_not_provided"}, status_code=403)
    
    try:
        client = AsyncOpenAI(api_key=key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
    except Exception as e:
        return JSONResponse({"ok": False, "error": "client_initialization_failed", "detail": str(e)}, status_code=500)

    model = data.get("model", DEFAULT_MODEL)
    messages = _build_openai_messages(data)
    config = data.get("config", {})
    temperature = config.get("temperature")
    top_p = config.get("top_p")

    if not any(msg['role'] == 'user' for msg in messages):
        return JSONResponse({"ok": False, "error": "empty_prompt"}, status_code=400)

    async def streamer():
        try:
            stream = await client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, top_p=top_p, stream=True
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content.encode("utf-8", errors="surrogatepass")
        except Exception as e:
            yield (json.dumps({"ok": False, "error": "upstream_error", "detail": str(e)}) + "\n").encode("utf-8", errors="surrogatepass")

    return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")
