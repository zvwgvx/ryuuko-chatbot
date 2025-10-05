# src/gateway/main.py
import datetime
import socket
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

# Import cấu hình từ module loader chung của dự án
from src.config import loader

# Import hàm logic chính từ module logic.py
from src.gateway.logic import handle_proxy_request

# ---------------- App init ----------------
app = FastAPI(title="LLM API Gateway", version="0.5-integrated")

# ---------------- Middleware and Request Validation (Giữ nguyên) ----------------
def _normalize_host(host: str) -> str:
    if not host: return ""
    return host.split(":", 1)[0].lower().strip()

def _is_allowed_request(request: Request) -> bool:
    # Logic này có thể không cần thiết nữa nếu gateway chỉ được gọi nội bộ
    # Nhưng giữ lại để có thể chạy độc lập
    host = _normalize_host(request.headers.get("host", ""))
    if host in ["127.0.0.1", "localhost"]: # Luôn cho phép truy cập local
        return True
    return False

@app.middleware("http")
async def allow_local_middleware(request: Request, call_next):
    # Đơn giản hóa middleware, chỉ cần cho phép localhost hoặc bỏ qua nếu không cần
    # if not _is_allowed_request(request):
    #     return PlainTextResponse("Forbidden", status_code=403)
    response = await call_next(request)
    return response

# ---------------- Client auth util ----------------
def _extract_client_key(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("x-api-key")

def _check_client_auth(request: Request) -> bool:
    key = _extract_client_key(request)
    if not key:
        return False
    # Sử dụng CLIENT_KEYS từ loader chung
    return key in loader.CLIENT_KEYS

# ---------------- API Endpoints ----------------
@app.get("/", include_in_schema=False)
async def root():
    return PlainTextResponse("API Gateway is running.", status_code=200)

@app.get("/health", summary="Health Check")
async def health_check():
    """
    Provides a simple health check for the gateway.
    """
    return {
        "ok": True,
        "status": "online",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "hostname": socket.gethostname(),
    }

@app.post("/proxy", summary="Proxy AI Requests")
async def proxy(request: Request):
    """
    Main endpoint to proxy requests to various AI providers.
    The request body is passed directly to the gateway's core logic.
    """
    if not _check_client_auth(request):
        return JSONResponse(
            content={"ok": False, "error": "Unauthorized: Invalid or missing API key."},
            status_code=401
        )

    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
    except Exception as e:
        return JSONResponse(
            content={"ok": False, "error": f"Invalid JSON body: {e}"},
            status_code=400
        )

    # === CORE CHANGE: Delegate all logic to the handler ===
    success, result = await handle_proxy_request(payload)
    # ======================================================

    if success:
        # Nếu thành công, `result` là một dict (nội dung JSON), trả về trực tiếp
        return JSONResponse(content=result, status_code=200)
    else:
        # Nếu thất bại, `result` là một chuỗi lỗi
        # Xác định mã trạng thái HTTP phù hợp dựa trên nội dung lỗi
        error_message = str(result)
        status_code = 500 # Internal Server Error mặc định

        if "not supported" in error_message or "not allowed" in error_message or "not specified" in error_message:
            status_code = 400 # Bad Request
        elif "not configured" in error_message or "unauthorized" in error_message:
            status_code = 403 # Forbidden
        elif "not implemented" in error_message:
            status_code = 501 # Not Implemented

        return JSONResponse(
            content={"ok": False, "error": error_message},
            status_code=status_code
        )

# ---------------- Main execution block ----------------
def run_gateway_server(host: str = "127.0.0.1", port: int = 8100):
    """
    Function to start the Uvicorn server.
    Can be called from the root main.py.
    """
    print(f"🚀 Starting AI Gateway server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    # Cho phép chạy file này độc lập để test
    run_gateway_server()