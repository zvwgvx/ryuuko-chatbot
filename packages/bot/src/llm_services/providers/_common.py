# providers/_common.py
from typing import Dict, Iterable, Tuple
import httpx
from fastapi.responses import StreamingResponse, JSONResponse
import asyncio

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade"
}

def filter_request_headers(headers: Dict[str, str]) -> Dict[str, str]:
    out = {}
    for k, v in headers.items():
        lk = k.lower()
        if lk in HOP_BY_HOP:
            continue
        if lk == "host":
            continue
        # Do not forward client Authorization unless you explicitly want to
        if lk == "authorization":
            continue
        out[k] = v
    return out

def filter_response_headers(headers: Dict[str, str]) -> Dict[str, str]:
    out = {}
    for k, v in headers.items():
        if k.lower() in HOP_BY_HOP:
            continue
        out[k] = v
    return out

async def forward_streaming(
    method: str,
    target_url: str,
    req_headers: Dict[str, str],
    request_stream,
    timeout: float = 100.0,
    connect_timeout: float = 5.0,
):
    """
    Trả StreamingResponse streaming dữ liệu từ upstream đến client.
    request_stream: starlette stream iterator (request.stream()) - có thể truyền trực tiếp cho httpx AsyncClient.content
    """
    timeout_cfg = httpx.Timeout(timeout, connect=connect_timeout)
    async with httpx.AsyncClient(timeout=timeout_cfg, follow_redirects=False) as client:
        try:
            upstream = client.stream(method, target_url, headers=req_headers, content=request_stream)
            async with upstream as resp:
                resp_headers = filter_response_headers(resp.headers)
                return StreamingResponse(resp.aiter_raw(), status_code=resp.status_code, headers=resp_headers)
        except httpx.RequestError as e:
            # upstream error -> trả 502
            return JSONResponse({"ok": False, "error": "upstream_error", "detail": str(e)}, status_code=502)
        except asyncio.CancelledError:
            # client closed connection early
            return JSONResponse({"ok": False, "error": "client_closed"}, status_code=499)
