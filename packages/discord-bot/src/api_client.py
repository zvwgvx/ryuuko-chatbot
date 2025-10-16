# /packages/discord-bot/src/api_client.py
import logging
import httpx
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple

from . import config

logger = logging.getLogger("DiscordBot.API")

client = httpx.AsyncClient(base_url=config.CORE_API_URL, timeout=300.0)

# --- Helper for Headers ---
def _get_auth_headers() -> Dict[str, str]:
    return {"X-API-Key": config.CORE_API_KEY}

async def _handle_api_error(e: httpx.HTTPStatusError) -> str:
    try:
        error_detail = e.response.json().get("detail", str(e))
    except Exception:
        error_detail = e.response.text or str(e)
    logger.error(f"Core API Error ({e.response.status_code}): {error_detail}")
    return str(error_detail)

# --- User & Chat Functions ---

async def get_dashboard_user_by_platform_id(platform: str, platform_user_id: int) -> Optional[Dict[str, Any]]:
    if not config.CORE_API_KEY: return None
    try:
        response = await client.get(f"/api/users/by-platform/{platform}/{platform_user_id}", headers=_get_auth_headers())
        if response.status_code == 404: return None
        response.raise_for_status()
        return response.json()
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Error fetching dashboard user for {platform_user_id}: {e}")
        return None

async def stream_chat_completions(platform: str, platform_user_id: str, messages: List[Dict[str, Any]], model: Optional[str] = None) -> AsyncGenerator[bytes, None]:
    headers = {**_get_auth_headers(), "Content-Type": "application/json", "Accept": "text/plain"}
    if not config.CORE_API_KEY: yield b"Error: Core Service API Key is not configured."; return
    payload = {"platform": platform, "platform_user_id": platform_user_id, "messages": messages, "model": model}
    try:
        async with client.stream("POST", "/api/chat/completions", headers=headers, json=payload) as response:
            if response.status_code != 200:
                error_body = await response.aread()
                yield f"Error: API returned status {response.status_code}\n{error_body.decode()}".encode('utf-8')
                return
            async for chunk in response.aiter_bytes(): yield chunk
    except httpx.RequestError as e:
        yield f"Error: Could not connect to the Core API at {config.CORE_API_URL}".encode('utf-8')

# --- Account Linking ---

async def link_account(code: str, platform: str, platform_user_id: str, display_name: str) -> Tuple[bool, str]:
    payload = {"code": code, "platform": platform, "platform_user_id": platform_user_id, "platform_display_name": display_name}
    try:
        response = await client.post("/api/link/submit-code", headers=_get_auth_headers(), json=payload)
        response.raise_for_status()
        return True, response.json().get("message", "Account linked successfully!")
    except httpx.HTTPStatusError as e: return False, await _handle_api_error(e)
    except httpx.RequestError as e: return False, f"Could not connect to the API: {e}"

async def unlink_account(platform: str, platform_user_id: str) -> Tuple[bool, str]:
    payload = {"platform": platform, "platform_user_id": platform_user_id}
    try:
        response = await client.post("/api/link/unlink", headers=_get_auth_headers(), json=payload)
        response.raise_for_status()
        return True, response.json().get("message", "Account unlinked successfully!")
    except httpx.HTTPStatusError as e: return False, await _handle_api_error(e)
    except httpx.RequestError as e: return False, f"Could not connect to the API: {e}"

# --- NEW: Admin Functions (using dashboard user_id) ---

async def admin_add_credits(user_id: str, amount: int) -> Tuple[bool, str]:
    try:
        response = await client.post(f"/api/admin/users/{user_id}/credits/add", headers=_get_auth_headers(), json={"amount": amount})
        response.raise_for_status()
        res_json = response.json()
        return True, f"Added {amount} credits to user {res_json.get('user_id')}. New balance: {res_json.get('new_value')}"
    except httpx.HTTPStatusError as e: return False, await _handle_api_error(e)
    except httpx.RequestError as e: return False, str(e)

async def admin_set_credits(user_id: str, amount: int) -> Tuple[bool, str]:
    try:
        response = await client.post(f"/api/admin/users/{user_id}/credits/set", headers=_get_auth_headers(), json={"amount": amount})
        response.raise_for_status()
        res_json = response.json()
        return True, f"Set credits for user {res_json.get('user_id')} to {res_json.get('new_value')}."
    except httpx.HTTPStatusError as e: return False, await _handle_api_error(e)
    except httpx.RequestError as e: return False, str(e)

async def admin_set_level(user_id: str, level: int) -> Tuple[bool, str]:
    try:
        response = await client.post(f"/api/admin/users/{user_id}/level/set", headers=_get_auth_headers(), json={"level": level})
        response.raise_for_status()
        res_json = response.json()
        return True, f"Set access level for user {res_json.get('user_id')} to {res_json.get('new_value')}."
    except httpx.HTTPStatusError as e: return False, await _handle_api_error(e)
    except httpx.RequestError as e: return False, str(e)
