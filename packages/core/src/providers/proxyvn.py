# providers/proxyvn.py
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

PROXY_BASE_URL = "https://proxyvn.top/v1"
DEFAULT_MODEL = "gpt-3.5-turbo"

# --- Helpers ---
def get_vietnam_timestamp() -> str:
    return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S GMT+7")

def _build_openai_messages(data: Dict) -> List[Dict[str, Any]]:
    messages = []

    timestamp_str = get_vietnam_timestamp()
    system_content = f"Current time: {timestamp_str}"

    user_system_instructions = data.get("system_instruction", [])
    if isinstance(user_system_instructions, list) and user_system_instructions:
        full_user_prompt = "\n".join(filter(None, [str(s).strip() for s in user_system_instructions]))
        if full_user_prompt:
            system_content += f"\n\n{full_user_prompt}"

    messages.append({"role": "system", "content": system_content})

    for msg in data.get("messages", []) or []:
        if not isinstance(msg, dict) or "role" not in msg or msg["role"] == "system":
            continue
        openai_role = "assistant" if msg["role"] in ("assistant", "model") else "user"
        messages.append({"role": openai_role, "content": msg["content"]})

    return messages


async def forward(request: Request, data: Dict, api_key: Optional[str]):
    if AsyncOpenAI is None:
        return JSONResponse(
            {"ok": False, "error": "dependency_not_found", "detail": _IMPORT_ERROR},
            status_code=500,
        )

    key = api_key or os.getenv("PROXYVN_API_KEY")
    if not key:
        return JSONResponse(
            {"ok": False, "error": "api_key_not_provided", "detail": "PROXYVN_API_KEY is not set."},
            status_code=403,
        )

    try:
        client = AsyncOpenAI(
            api_key=key,
            base_url=PROXY_BASE_URL,
        )
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": "client_initialization_failed", "detail": str(e)},
            status_code=500,
        )

    model = data.get("model", DEFAULT_MODEL)
    messages = _build_openai_messages(data)
    config = data.get("config", {})
    temperature = config.get("temperature")
    top_p = config.get("top_p")

    if not any(msg['role'] == 'user' for msg in messages):
        return JSONResponse(
            {"ok": False, "error": "empty_prompt", "detail": "No content to send."},
            status_code=400,
        )

    async def streamer():
        try:
            stream = await client.chat.completions.create(
                model=model,
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
