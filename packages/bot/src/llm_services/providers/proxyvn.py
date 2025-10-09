# providers/openai.py
import os
import asyncio
import json
from typing import Dict, Optional, Any
from fastapi import Request
from fastapi.responses import StreamingResponse, JSONResponse

# HTTP client for talking to PROXYVN
try:
    import httpx
except Exception as e:
    httpx = None
    _HTTPX_IMPORT_ERROR = e

# Bắt buộc gọi tới PROXYVN
PROXYVN_BASE = "https://proxyvn.top"  # no trailing slash


def _extract_prompt(data: Dict) -> str:
    """
    Lấy ra một chuỗi prompt duy nhất từ payload của client.
    - Nếu data là dict và có 'prompt' là str -> trả về đó
    - Nếu data là dict và có 'messages' list -> lấy messages[0].content
    - Nếu data là dict but không có prompt -> stringify toàn bộ data
    - Nếu data không phải dict -> stringify
    """
    if not isinstance(data, dict):
        return json.dumps(data)

    prompt = data.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt.strip()

    msgs = data.get("messages")
    if isinstance(msgs, list) and msgs:
        first = msgs[0]
        if isinstance(first, dict):
            content = first.get("content") or first.get("text") or ""
            if isinstance(content, dict):
                content = content.get("text", "")
            return str(content)

    # fallback: stringify the whole dict
    return json.dumps(data)


async def forward(request: Request, data: Dict, api_key: Optional[str]):
    """
    Forward request to PROXYVN but only send a single-field payload containing the prompt.
    Không gửi model, temperature, stream hay bất kỳ tham số nào khác.

    - request: FastAPI Request
    - data: parsed JSON body from client
    - api_key: upstream API key (string) OR use PROXYVN_API_KEY env var
    """
    if httpx is None:
        return JSONResponse({"ok": False, "error": "httpx package not installed", "detail": str(_HTTPX_IMPORT_ERROR)}, status_code=500)

    key = api_key or os.getenv("PROXYVN_API_KEY")
    if not key:
        return JSONResponse({"ok": False, "error": "proxyvn api key not provided (PROXYVN_API_KEY)"}, status_code=403)

    # build payload: ONLY send the prompt string
    prompt_str = _extract_prompt(data)
    payload = {"prompt": prompt_str}

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "proxyvn-client/1.0",
    }

    q: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def _push_error_and_close(exc_msg: str):
        loop.call_soon_threadsafe(q.put_nowait, {"__error": exc_msg})
        loop.call_soon_threadsafe(q.put_nowait, None)

    def producer():
        """
        Blocking producer running in a thread: POST to PROXYVN and stream chunks into asyncio queue.
        Behavior:
          - We POST payload={"prompt": "..."}
          - We attempt to capture both SSE "data: ..." lines and raw chunked JSON/text
        """
        url = PROXYVN_BASE.rstrip("/") + "/v1/chat/completions"
        try:
            with httpx.Client(timeout=None) as client:
                with client.stream("POST", url, headers=headers, json=payload, timeout=None) as resp:
                    try:
                        resp.raise_for_status()
                    except Exception as e:
                        try:
                            body = resp.text
                        except Exception:
                            body = "<could not read body>"
                        _push_error_and_close(f"upstream_http_error: {str(e)} - body: {body}")
                        return

                    # iterate by lines first (SSE-like)
                    try:
                        for raw_line in resp.iter_lines():
                            if raw_line is None:
                                continue
                            if isinstance(raw_line, bytes):
                                line = raw_line.decode("utf-8", errors="ignore")
                            else:
                                line = str(raw_line)

                            line = line.strip()
                            if not line:
                                continue

                            if line.startswith("data:"):
                                data_part = line[len("data:"):].strip()
                                if data_part == "[DONE]":
                                    break
                                try:
                                    parsed = json.loads(data_part)
                                    loop.call_soon_threadsafe(q.put_nowait, json.dumps(parsed))
                                except Exception:
                                    loop.call_soon_threadsafe(q.put_nowait, data_part)
                                continue

                            # try parse as JSON line
                            try:
                                parsed = json.loads(line)
                                loop.call_soon_threadsafe(q.put_nowait, json.dumps(parsed))
                            except Exception:
                                loop.call_soon_threadsafe(q.put_nowait, line)

                    except Exception:
                        # ignore line-iteration errors and fallback to bytes
                        pass

                    # also ensure we capture any remaining byte chunks
                    try:
                        for chunk in resp.iter_bytes():
                            if not chunk:
                                continue
                            try:
                                text = chunk.decode("utf-8", errors="ignore").strip()
                                if not text:
                                    continue
                                # handle SSE fragments inside chunk
                                for part in text.splitlines():
                                    part = part.strip()
                                    if not part:
                                        continue
                                    if part.startswith("data:"):
                                        data_part = part[len("data:"):].strip()
                                        if data_part == "[DONE]":
                                            raise StopIteration
                                        try:
                                            parsed = json.loads(data_part)
                                            loop.call_soon_threadsafe(q.put_nowait, json.dumps(parsed))
                                        except Exception:
                                            loop.call_soon_threadsafe(q.put_nowait, data_part)
                                    else:
                                        try:
                                            parsed = json.loads(part)
                                            loop.call_soon_threadsafe(q.put_nowait, json.dumps(parsed))
                                        except Exception:
                                            loop.call_soon_threadsafe(q.put_nowait, part)
                            except StopIteration:
                                break
                            except Exception:
                                continue
                    except Exception:
                        pass

        except Exception as e:
            _push_error_and_close(str(e))
            return
        finally:
            loop.call_soon_threadsafe(q.put_nowait, None)

    # start producer in background thread
    asyncio.create_task(asyncio.to_thread(producer))

    async def streamer():
        try:
            while True:
                item = await q.get()
                if item is None:
                    break
                if isinstance(item, dict) and item.get("__error"):
                    yield (json.dumps({"ok": False, "error": "upstream_error", "detail": item.get("__error")}) + "\n").encode("utf-8")
                    break
                if not isinstance(item, (str, bytes)):
                    item = str(item)
                b = item.encode("utf-8") if isinstance(item, str) else item
                yield b
        except asyncio.CancelledError:
            return

    return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")
