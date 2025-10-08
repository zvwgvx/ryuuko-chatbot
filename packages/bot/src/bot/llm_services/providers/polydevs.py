import os
import asyncio
import json
import base64
from typing import Dict, Optional, Any, List
from pathlib import Path
from fastapi import Request
from fastapi.responses import StreamingResponse, JSONResponse

try:
    from google import genai
    from google.genai import types
except Exception as e:
    genai = None
    types = None
    _IMPORT_ERROR = e

DEFAULT_MODEL = "ryuuko-r1-mini"

# Global variable để lưu instructions
INSTRUCTIONS = None
INSTRUCTIONS_LOAD_ERROR = None


def load_instructions():
    """Load instructions từ file JSON - BẮT BUỘC phải có file"""
    global INSTRUCTIONS_LOAD_ERROR

    try:
        # Thử nhiều vị trí có thể
        possible_paths = [
            Path(__file__).parent / "instructions.json",
            Path.cwd() / "instructions.json",
            Path(__file__).parent.parent / "instructions.json",
            Path.cwd() / "scripts" / "instructions.json",
        ]

        instruction_file = None
        tried_paths = []

        for path in possible_paths:
            tried_paths.append(str(path.absolute()))
            print(f"[INSTRUCTION LOADER] Checking: {path.absolute()}")
            if path.exists():
                instruction_file = path
                print(f"[INSTRUCTION LOADER] ✓ Found at: {path.absolute()}")
                break
            else:
                print(f"[INSTRUCTION LOADER] ✗ Not found at: {path.absolute()}")

        if instruction_file is None:
            error_msg = f"CRITICAL: instructions.json not found! Tried paths:\n" + "\n".join(tried_paths)
            print(f"[INSTRUCTION LOADER] {error_msg}")
            INSTRUCTIONS_LOAD_ERROR = error_msg
            return None

        # Load và validate file
        with open(instruction_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[INSTRUCTION LOADER] Successfully loaded JSON from {instruction_file}")

            # Validate structure
            if not isinstance(data, dict):
                error_msg = f"Invalid instructions.json: Root must be object, got {type(data)}"
                print(f"[INSTRUCTION LOADER] {error_msg}")
                INSTRUCTIONS_LOAD_ERROR = error_msg
                return None

            if "vietnamese" not in data:
                error_msg = "Invalid instructions.json: Missing 'vietnamese' key"
                print(f"[INSTRUCTION LOADER] {error_msg}")
                INSTRUCTIONS_LOAD_ERROR = error_msg
                return None

            if "english" not in data:
                error_msg = "Invalid instructions.json: Missing 'english' key"
                print(f"[INSTRUCTION LOADER] {error_msg}")
                INSTRUCTIONS_LOAD_ERROR = error_msg
                return None

            # Check if instructions are not empty
            vn_instruction = data.get("vietnamese", {})
            en_instruction = data.get("english", {})

            if isinstance(vn_instruction, dict):
                vn_text = vn_instruction.get("system_instruction", "")
            else:
                vn_text = str(vn_instruction)

            if isinstance(en_instruction, dict):
                en_text = en_instruction.get("system_instruction", "")
            else:
                en_text = str(en_instruction)

            if not vn_text or not en_text:
                error_msg = "Invalid instructions.json: Vietnamese or English instruction is empty"
                print(f"[INSTRUCTION LOADER] {error_msg}")
                INSTRUCTIONS_LOAD_ERROR = error_msg
                return None

            print(f"[INSTRUCTION LOADER] ✓ Validated successfully")
            print(f"[INSTRUCTION LOADER] - Vietnamese instruction: {len(vn_text)} chars")
            print(f"[INSTRUCTION LOADER] - English instruction: {len(en_text)} chars")

            return data

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse instructions.json: {e}"
        print(f"[INSTRUCTION LOADER] {error_msg}")
        INSTRUCTIONS_LOAD_ERROR = error_msg
        return None
    except Exception as e:
        error_msg = f"Unexpected error loading instructions.json: {e}"
        print(f"[INSTRUCTION LOADER] {error_msg}")
        INSTRUCTIONS_LOAD_ERROR = error_msg
        return None


# Load instructions khi khởi động module
print("\n" + "=" * 60)
print("[INSTRUCTION LOADER] Starting instruction loading...")
INSTRUCTIONS = load_instructions()
if INSTRUCTIONS is None:
    print("[INSTRUCTION LOADER] ⚠️ FAILED TO LOAD INSTRUCTIONS!")
    print("[INSTRUCTION LOADER] The service will return errors until instructions.json is properly configured")
else:
    print("[INSTRUCTION LOADER] ✓ Instructions loaded successfully!")
print("=" * 60 + "\n")


def get_instruction_by_model(model: str) -> Optional[str]:
    """
    Trả về instruction phù hợp dựa trên model name
    Returns None nếu không load được instructions
    """
    if INSTRUCTIONS is None:
        print(f"[GET INSTRUCTION] ERROR: Instructions not loaded! {INSTRUCTIONS_LOAD_ERROR}")
        return None

    if model and "eng" in model.lower():
        instruction = INSTRUCTIONS.get("english", {})
        if isinstance(instruction, dict):
            text = instruction.get("system_instruction", "")
            if isinstance(text, list):
                text = "\n".join(text)
        else:
            text = str(instruction) if instruction else ""

        if not text:
            print(f"[GET INSTRUCTION] WARNING: English instruction is empty!")
            return None

        print(f"[GET INSTRUCTION] Using English instruction ({len(text)} chars) for model: {model}")
        return text
    else:
        instruction = INSTRUCTIONS.get("vietnamese", {})
        if isinstance(instruction, dict):
            text = instruction.get("system_instruction", "")
            if isinstance(text, list):
                text = "\n".join(text)
        else:
            text = str(instruction) if instruction else ""

        if not text:
            print(f"[GET INSTRUCTION] WARNING: Vietnamese instruction is empty!")
            return None

        print(f"[GET INSTRUCTION] Using Vietnamese instruction ({len(text)} chars) for model: {model}")
        return text


def _extract_messages_to_contents(messages: List[Dict]) -> List[Any]:
    """
    ✅ FIXED: Convert messages array to Gemini Content objects with IMAGE SUPPORT
    Supports both:
    - Text-only messages: {"role": "user", "content": "text"}
    - Multimodal messages: {"role": "user", "parts": [{"text": "..."}, {"inline_data": {...}}]}
    """
    contents = []

    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue

        role = msg.get("role", "user")

        # Skip system messages (handled separately)
        if role == "system":
            continue

        # Map roles: assistant/model -> model for Gemini
        if role in ("assistant", "model"):
            gemini_role = "model"
        else:
            gemini_role = "user"

        # ✅ CHECK FOR MULTIMODAL MESSAGE (with "parts")
        if "parts" in msg:
            parts_array = msg.get("parts", [])
            if not isinstance(parts_array, list) or not parts_array:
                continue

            gemini_parts = []

            for part in parts_array:
                if not isinstance(part, dict):
                    continue

                # Handle text part
                if "text" in part:
                    text_content = part.get("text", "")
                    if isinstance(text_content, str) and text_content.strip():
                        gemini_parts.append(types.Part.from_text(text=text_content))
                        print(f"[MESSAGES] Message {i}: Added text part ({len(text_content)} chars)")

                # ✅ Handle image part (inline_data)
                elif "inline_data" in part:
                    inline = part.get("inline_data", {})
                    if isinstance(inline, dict):
                        mime_type = inline.get("mime_type")
                        base64_data = inline.get("data")

                        if mime_type and base64_data:
                            try:
                                # Decode base64 to bytes
                                image_bytes = base64.b64decode(base64_data)

                                # Create image part
                                image_part = types.Part.from_bytes(
                                    data=image_bytes,
                                    mime_type=mime_type
                                )
                                gemini_parts.append(image_part)
                                print(f"[MESSAGES] Message {i}: Added image part ({mime_type}, {len(image_bytes)} bytes)")
                            except Exception as e:
                                print(f"[MESSAGES] Error decoding image in message {i}: {e}")

            # Add content if we have valid parts
            if gemini_parts:
                try:
                    contents.append(
                        types.Content(
                            role=gemini_role,
                            parts=gemini_parts
                        )
                    )
                    print(f"[MESSAGES] Added multimodal message {i}: role={gemini_role}, {len(gemini_parts)} parts")
                except Exception as e:
                    print(f"[MESSAGES] Error creating Content for multimodal message {i}: {e}")

        # ✅ TEXT-ONLY MESSAGE (backward compatible)
        elif "content" in msg:
            content = msg.get("content", "")

            # Convert content to string
            if isinstance(content, dict):
                text = content.get("text", "")
                if not text:
                    text = json.dumps(content)
            elif isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        text_parts.append(part)
                text = "\n".join(text_parts)
            else:
                text = str(content)

            # Add to contents if not empty
            if text.strip():
                try:
                    contents.append(
                        types.Content(
                            role=gemini_role,
                            parts=[types.Part.from_text(text=text)]
                        )
                    )
                    print(f"[MESSAGES] Added text message {i}: role={gemini_role}, text_length={len(text)}")
                except Exception as e:
                    print(f"[MESSAGES] Error creating Content for text message {i}: {e}")

    return contents


def _extract_prompt_from_data(data: Dict) -> str:
    """
    Fallback: Extract prompt as string when messages format is not available
    """
    if not isinstance(data, dict):
        return json.dumps(data)

    prompt = data.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt.strip()

    return json.dumps(data)


async def forward(request: Request, data: Dict, api_key: Optional[str]):
    """
    Forward cho polydevs models using Gemini
    ✅ FIXED: Now properly handles multimodal messages with images
    """

    # Check instructions đã load chưa
    if INSTRUCTIONS is None:
        error_detail = f"Instructions not loaded. {INSTRUCTIONS_LOAD_ERROR or 'Please ensure instructions.json exists in the correct location.'}"
        print(f"[FORWARD] ERROR: {error_detail}")
        return JSONResponse(
            {"ok": False, "error": "configuration_error", "detail": error_detail},
            status_code=500
        )

    if genai is None or types is None:
        return JSONResponse(
            {"ok": False, "error": "google-genai not installed", "detail": str(_IMPORT_ERROR)},
            status_code=500
        )

    key = api_key or os.getenv("POLYDEVS_API_KEY")
    if not key:
        return JSONResponse(
            {"ok": False, "error": "gemini/ai studio api key not provided"},
            status_code=403
        )

    model = data.get("model") or DEFAULT_MODEL
    original_model = model

    print(f"\n[FORWARD] Processing request with model: {original_model}")

    # Model mapping cho ryuuko series
    model_mapping = {
        "ryuuko-r1-vnm-pro": "gemini-2.5-pro",
        "ryuuko-r1-vnm-mini": "gemini-2.5-flash",
        "ryuuko-r1-vnm-nano": "gemini-2.5-flash-lite",
        "ryuuko-r1-eng-pro": "gemini-2.5-pro",
        "ryuuko-r1-eng-mini": "gemini-2.5-flash",
        "ryuuko-r1-eng-nano": "gemini-2.5-flash-lite"
    }

    if model in model_mapping:
        model = model_mapping[model]
        print(f"[FORWARD] Mapped to Gemini model: {model}")

    # Extract config
    cfg: Dict[str, Any] = data.get("config", {}) or {}
    temperature = cfg.get("temperature", None)
    top_p = cfg.get("top_p", None)
    tools_enabled = bool(cfg.get("tools", False))
    thinking_budget = cfg.get("thinking_budget", -1)

    # Build thinking config
    thinking_cfg = None
    if thinking_budget != -1:
        thinking_cfg = types.ThinkingConfig(thinking_budget=thinking_budget)

    # ✅ Convert messages to Gemini format with image support
    messages = data.get("messages", [])
    contents = []

    if messages:
        print(f"[FORWARD] Processing {len(messages)} messages from request")
        contents = _extract_messages_to_contents(messages)
        print(f"[FORWARD] Converted to {len(contents)} Gemini Content objects")

        # Debug log
        for i, content in enumerate(contents[:3]):
            parts_info = []
            for part in content.parts:
                if hasattr(part, 'text'):
                    parts_info.append(f"text:{len(part.text)}chars")
                elif hasattr(part, 'inline_data'):
                    parts_info.append(f"image:{part.mime_type if hasattr(part, 'mime_type') else 'unknown'}")
            print(f"[FORWARD] Content[{i}] role={content.role}, parts=[{', '.join(parts_info)}]")
    else:
        # Fallback
        prompt_text = _extract_prompt_from_data(data)
        print(f"[FORWARD] No messages found, using prompt: {prompt_text[:100]}...")
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt_text)]
            )
        ]

    # Build tools list
    tools_list = None
    if tools_enabled:
        try:
            tools_list = []

            try:
                tools_list.append(types.Tool(google_search=types.GoogleSearch()))
                print("[FORWARD] Added google_search tool")
            except Exception as e:
                print(f"[FORWARD] Failed to add google_search: {e}")

            try:
                tools_list.append(types.Tool(url_context=types.UrlContext()))
                print("[FORWARD] Added url_context tool")
            except Exception as e:
                print(f"[FORWARD] Failed to add url_context: {e}")

            try:
                tools_list.append(types.Tool(code_execution=types.ToolCodeExecution()))
                print("[FORWARD] Added code_execution tool")
            except Exception as e:
                print(f"[FORWARD] Failed to add code_execution: {e}")

            if not tools_list:
                tools_list = None

        except Exception as e:
            print(f"[FORWARD] Error building tools: {e}")
            tools_list = None

    # Get instruction
    ryuuko_instruction = get_instruction_by_model(original_model)

    if ryuuko_instruction is None:
        error_msg = f"Failed to get instruction for model {original_model}"
        print(f"[FORWARD] ERROR: {error_msg}")
        return JSONResponse(
            {"ok": False, "error": "instruction_error", "detail": error_msg},
            status_code=500
        )

    print(f"[FORWARD] Instruction loaded ({len(ryuuko_instruction)} chars)")

    sys_parts = [types.Part.from_text(text=ryuuko_instruction.strip())]

    # Build GenerateContentConfig
    gen_cfg_kwargs = {}
    if temperature is not None:
        gen_cfg_kwargs["temperature"] = float(temperature)
    if top_p is not None:
        gen_cfg_kwargs["top_p"] = float(top_p)
    if thinking_cfg is not None:
        gen_cfg_kwargs["thinking_config"] = thinking_cfg
    if tools_list:
        gen_cfg_kwargs["tools"] = tools_list
    if sys_parts:
        gen_cfg_kwargs["system_instruction"] = sys_parts

    generate_cfg = None
    try:
        generate_cfg = types.GenerateContentConfig(**gen_cfg_kwargs)
        print("[FORWARD] Created GenerateContentConfig successfully")
    except TypeError as e:
        print(f"[FORWARD] TypeError creating config: {e}")
        safe_kwargs = {}
        if "temperature" in gen_cfg_kwargs:
            safe_kwargs["temperature"] = gen_cfg_kwargs["temperature"]
        if "thinking_config" in gen_cfg_kwargs:
            safe_kwargs["thinking_config"] = gen_cfg_kwargs["thinking_config"]
        if "tools" in gen_cfg_kwargs:
            safe_kwargs["tools"] = gen_cfg_kwargs["tools"]
        if "system_instruction" in gen_cfg_kwargs:
            safe_kwargs["system_instruction"] = gen_cfg_kwargs["system_instruction"]
        try:
            generate_cfg = types.GenerateContentConfig(**safe_kwargs)
            print("[FORWARD] Created config with safe kwargs")
        except Exception as e2:
            print(f"[FORWARD] Failed to create config: {e2}")

    # Create client
    try:
        client = genai.Client(api_key=key)
        print("[FORWARD] Created Gemini client")
    except Exception as e:
        print(f"[FORWARD] Error creating client: {e}")
        return JSONResponse(
            {"ok": False, "error": "failed_to_create_client", "detail": str(e)},
            status_code=500
        )

    # Setup async queue
    loop = asyncio.get_event_loop()
    q: asyncio.Queue = asyncio.Queue()

    def producer():
        """Run in thread - iterate stream and push to queue"""
        try:
            # Try non-streaming first
            try:
                if generate_cfg is not None:
                    response = client.models.generate_content(
                        model=model,
                        contents=contents,
                        config=generate_cfg,
                    )
                else:
                    response = client.models.generate_content(
                        model=model,
                        contents=contents,
                    )

                if hasattr(response, 'candidates') and response.candidates:
                    cand = response.candidates[0]
                    if hasattr(cand, 'content') and cand.content and hasattr(cand.content, 'parts'):
                        complete_text = ""
                        for part in cand.content.parts:
                            if hasattr(part, 'text') and part.text:
                                complete_text += part.text

                        if complete_text.strip():
                            print(f"[PRODUCER] Sending response: {len(complete_text)} chars")
                            loop.call_soon_threadsafe(q.put_nowait, complete_text)
                            loop.call_soon_threadsafe(q.put_nowait, None)
                            return

            except Exception as e:
                print(f"[PRODUCER] Non-streaming failed: {e}")

            # Fallback to streaming
            print("[PRODUCER] Using streaming mode")
            if generate_cfg is not None:
                stream = client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=generate_cfg,
                )
            else:
                stream = client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                )

            chunk_count = 0
            for chunk in stream:
                chunk_count += 1
                try:
                    if not chunk or not hasattr(chunk, 'candidates') or not chunk.candidates:
                        continue

                    cand = chunk.candidates[0]
                    if not hasattr(cand, 'content') or not cand.content:
                        continue

                    if hasattr(cand.content, 'parts'):
                        for part in cand.content.parts:
                            if hasattr(part, 'text') and part.text:
                                loop.call_soon_threadsafe(q.put_nowait, part.text)

                except Exception as chunk_error:
                    print(f"[PRODUCER] Error in chunk {chunk_count}: {chunk_error}")
                    continue

            print(f"[PRODUCER] Stream completed: {chunk_count} chunks")

        except Exception as e:
            print(f"[PRODUCER] Error: {e}")
            loop.call_soon_threadsafe(q.put_nowait, {"__error": str(e)})
        finally:
            loop.call_soon_threadsafe(q.put_nowait, None)

    # Start producer
    asyncio.create_task(asyncio.to_thread(producer))

    async def streamer():
        """Async generator for streaming response"""
        try:
            while True:
                item = await q.get()
                if item is None:
                    break
                if isinstance(item, dict) and item.get("__error"):
                    err = item.get("__error")
                    yield (json.dumps({"ok": False, "error": "upstream_error", "detail": err}) + "\n").encode("utf-8")
                    break

                if isinstance(item, str):
                    yield item.encode("utf-8")
                elif isinstance(item, bytes):
                    yield item
                else:
                    yield str(item).encode("utf-8")

        except asyncio.CancelledError:
            return

    return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")