# /packages/ryuuko-api/src/providers/polydevs.py
import asyncio
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

DEFAULT_MODEL = "ryuuko-r1-mini"

def get_vietnam_timestamp() -> str:
    return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S GMT+7")

# --- Instruction Loading Logic ---
INSTRUCTIONS = None
INSTRUCTIONS_LOAD_ERROR = None

def load_instructions() -> Optional[Dict[str, str]]:
    """Loads system instructions from vietnamese.txt and english.txt."""
    global INSTRUCTIONS_LOAD_ERROR
    try:
        # Path is relative to the ryuuko-api package root
        instructions_dir = Path(__file__).resolve().parents[2] / "instructions"
        
        vn_file = instructions_dir / "vietnamese.txt"
        en_file = instructions_dir / "english.txt"

        if not vn_file.exists() or not en_file.exists():
            INSTRUCTIONS_LOAD_ERROR = f"Instruction files not found in {instructions_dir.absolute()}"
            return None

        with open(vn_file, 'r', encoding='utf-8') as f:
            vn_instruction = f.read().strip()
        with open(en_file, 'r', encoding='utf-8') as f:
            en_instruction = f.read().strip()

        if not vn_instruction or not en_instruction:
            INSTRUCTIONS_LOAD_ERROR = "Instruction file is empty."
            return None

        return {"vietnamese": vn_instruction, "english": en_instruction}

    except Exception as e:
        INSTRUCTIONS_LOAD_ERROR = f"Unexpected error loading instruction files: {e}"
        return None

INSTRUCTIONS = load_instructions()
if INSTRUCTIONS is None:
    print(f"[POLYDEVS-PROVIDER] ⚠️ FAILED TO LOAD INSTRUCTIONS: {INSTRUCTIONS_LOAD_ERROR}")
else:
    print("[POLYDEVS-PROVIDER] ✓ Instructions loaded successfully!")

def get_instruction_by_model(model: str) -> Optional[str]:
    """Gets the appropriate instruction string based on the model name."""
    if INSTRUCTIONS is None: return None
    key = "english" if model and "eng" in model.lower() else "vietnamese"
    return INSTRUCTIONS.get(key)

def _build_openai_messages(data: Dict, system_prompt: str) -> List[Dict[str, Any]]:
    """Builds the message payload, prepending the timestamp to the system prompt."""
    messages = []
    timestamp_str = get_vietnam_timestamp()
    # Naturally integrate the timestamp into the system prompt
    final_system_prompt = f"The current date and time is {timestamp_str}. {system_prompt}"
    messages.append({"role": "system", "content": final_system_prompt})

    for msg in data.get("messages", []) or []:
        if not isinstance(msg, dict) or "role" not in msg or msg["role"] == "system": continue
        messages.append({"role": msg["role"], "content": msg["content"]})

    return messages

async def forward(request: Request, data: Dict, api_key: Optional[str]):
    """Forwards the request to the Polydevs (Gemini) provider."""
    if AsyncOpenAI is None: return JSONResponse({"ok": False, "error": "dependency_not_found"}, status_code=500)
    if INSTRUCTIONS is None: return JSONResponse({"ok": False, "error": "configuration_error", "detail": INSTRUCTIONS_LOAD_ERROR}, status_code=500)
    
    key = api_key or os.getenv("POLYDEVS_API_KEY")
    if not key: return JSONResponse({"ok": False, "error": "api_key_not_provided"}, status_code=403)

    try: #https://generativelanguage.googleapis.com/v1beta/openai/
        client = AsyncOpenAI(api_key=key, base_url="https://proxyvn.top/")
    except Exception as e:
        return JSONResponse({"ok": False, "error": "client_initialization_failed", "detail": str(e)}, status_code=500)

    original_model = data.get("model", DEFAULT_MODEL)
    model_mapping = {
        "ryuuko-r1-vnm-pro": "gemini-2.5-pro", "ryuuko-r1-vnm-mini": "gemini-2.5-flash", "ryuuko-r1-vnm-nano": "gemini-2.5-flash",
        "ryuuko-r1-eng-pro": "gemini-2.5-pro", "ryuuko-r1-eng-mini": "gemini-2.5-flash", "ryuuko-r1-eng-nano": "gemini-2.5-flash",
    }
    final_model = model_mapping.get(original_model, original_model)

    system_prompt = get_instruction_by_model(original_model)
    if not system_prompt: return JSONResponse({"ok": False, "error": "instruction_error"}, status_code=500)

    messages = _build_openai_messages(data, system_prompt)
    if not any(m["role"] == "user" for m in messages): return JSONResponse({"ok": False, "error": "empty_prompt"}, status_code=400)

    config = data.get("config", {})
    async def streamer():
        try:
            stream = await client.chat.completions.create(model=final_model, messages=messages, temperature=config.get("temperature"), top_p=config.get("top_p"), stream=True)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content.encode("utf-8", errors="surrogatepass")
        except Exception as e:
            yield (json.dumps({"ok": False, "error": "upstream_error", "detail": str(e)}) + "\n").encode("utf-8", errors="surrogatepass")

    return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")
