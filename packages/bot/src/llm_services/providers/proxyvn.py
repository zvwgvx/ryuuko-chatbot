# providers/proxyvn.py
import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse

# Sử dụng AsyncOpenAI client cho môi trường asyncio
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None
    _IMPORT_ERROR = "openai library not found. Please install it with 'pip install openai'"

# Endpoint của dịch vụ proxy
PROXY_BASE_URL = "https://proxyvn.top/v1"
DEFAULT_MODEL = "gpt-3.5-turbo"  # Một model mặc định hợp lý cho proxy

def _build_openai_messages(data: Dict) -> List[Dict[str, Any]]:
    """
    Xây dựng danh sách 'messages' theo định dạng của OpenAI từ dữ liệu yêu cầu.
    """
    messages = []

    system_instructions = data.get("system_instruction", [])
    if isinstance(system_instructions, list) and system_instructions:
        full_system_prompt = "\n".join(filter(None, [str(s).strip() for s in system_instructions]))
        if full_system_prompt:
            messages.append({"role": "system", "content": full_system_prompt})

    if "messages" in data and isinstance(data["messages"], list):
        for msg in data["messages"]:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                if msg["role"] == "system":
                    continue
                messages.append({"role": msg["role"], "content": msg["content"]})
    elif "prompt" in data and isinstance(data["prompt"], str):
        messages.append({"role": "user", "content": data["prompt"]})

    return messages


async def forward(request: Request, data: Dict, api_key: Optional[str]):
    """
    Chuyển tiếp yêu cầu đến một endpoint tương thích OpenAI (ProxyVN) bằng AsyncOpenAI SDK.
    """
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

    if not messages:
        return JSONResponse(
            {"ok": False, "error": "empty_prompt", "detail": "Không có nội dung để gửi."},
            status_code=400,
        )

    async def streamer():
        """
        Async generator để gọi API và yield các chunk dữ liệu.
        """
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
