# /packages/discord-bot/src/api_client.py
import logging
import httpx
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple, Set

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

# --- Chat Completions ---
async def stream_chat_completions(payload: Dict[str, Any]) -> AsyncGenerator[bytes, None]:
    headers = {**_get_auth_headers(), "Content-Type": "application/json", "Accept": "text/plain"}
    if not config.CORE_API_KEY: yield b"Error: Core Service API Key is not configured."; return
    try:
        async with client.stream("POST", "/api/v1/chat/completions", headers=headers, json=payload) as response:
            if response.status_code != 200:
                error_body = await response.aread()
                yield f"Error: Core API returned status {response.status_code}\n{error_body.decode()}".encode('utf-8')
                return
            async for chunk in response.aiter_bytes(): yield chunk
    except httpx.RequestError as e:
        yield f"Error: Could not connect to Core Service at {config.CORE_API_URL}".encode('utf-8')

# --- Public & User Functions ---
async def list_available_models() -> Optional[List[Dict[str, Any]]]:
    try:
        response = await client.get("/api/v1/models", headers=_get_auth_headers())
        response.raise_for_status()
        return response.json()
    except (httpx.RequestError, httpx.HTTPStatusError): return None

async def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
    try:
        response = await client.get(f"/api/v1/users/{user_id}", headers=_get_auth_headers())
        response.raise_for_status()
        return response.json()
    except (httpx.RequestError, httpx.HTTPStatusError): return None

async def update_user_config(user_id: int, model: Optional[str] = None, system_prompt: Optional[str] = None) -> Tuple[bool, str]:
    payload = {}
    if model is not None: payload["model"] = model
    if system_prompt is not None: payload["system_prompt"] = system_prompt
    if not payload: return False, "No data provided."
    try:
        response = await client.put(f"/api/v1/users/{user_id}/config", headers=_get_auth_headers(), json=payload)
        response.raise_for_status()
        return True, response.json().get("message", "Success!")
    except httpx.HTTPStatusError as e: return False, await _handle_api_error(e)
    except httpx.RequestError as e: return False, str(e)

async def get_user_memory(user_id: int) -> Optional[List[Dict[str, Any]]]:
    try:
        response = await client.get(f"/api/v1/users/{user_id}/memory", headers=_get_auth_headers())
        response.raise_for_status()
        return response.json()
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Failed to get memory for user {user_id}: {e}")
        return None

async def clear_user_memory(user_id: int) -> bool:
    try:
        response = await client.delete(f"/api/v1/users/{user_id}/memory", headers=_get_auth_headers())
        response.raise_for_status()
        return True
    except (httpx.RequestError, httpx.HTTPStatusError): return False

# --- Admin Functions ---
async def add_model(name: str, cost: int, level: int) -> Tuple[bool, str]:
    payload = {"model_name": name, "credit_cost": cost, "access_level": level}
    try:
        response = await client.post("/api/v1/admin/models", headers=_get_auth_headers(), json=payload)
        response.raise_for_status()
        return True, response.json().get("message", "Success!")
    except httpx.HTTPStatusError as e: return False, await _handle_api_error(e)
    except httpx.RequestError as e: return False, str(e)

async def remove_model(name: str) -> Tuple[bool, str]:
    try:
        response = await client.delete(f"/api/v1/admin/models/{name}", headers=_get_auth_headers())
        response.raise_for_status()
        return True, response.json().get("message", "Success!")
    except httpx.HTTPStatusError as e: return False, await _handle_api_error(e)
    except httpx.RequestError as e: return False, str(e)

async def add_user_credits(user_id: int, amount: int) -> Tuple[bool, str]:
    try:
        response = await client.put(f"/api/v1/admin/users/{user_id}/credits/add", headers=_get_auth_headers(), json={"amount": amount})
        response.raise_for_status()
        new_balance = response.json().get("new_balance", "N/A")
        return True, f"Success! New balance: {new_balance}"
    except httpx.HTTPStatusError as e: return False, await _handle_api_error(e)
    except httpx.RequestError as e: return False, str(e)

async def deduct_user_credits(user_id: int, amount: int) -> Tuple[bool, str]:
    try:
        response = await client.put(f"/api/v1/admin/users/{user_id}/credits/deduct", headers=_get_auth_headers(), json={"amount": amount})
        response.raise_for_status()
        new_balance = response.json().get("new_balance", "N/A")
        return True, f"Success! New balance: {new_balance}"
    except httpx.HTTPStatusError as e: return False, await _handle_api_error(e)
    except httpx.RequestError as e: return False, str(e)

async def set_user_credits(user_id: int, amount: int) -> Tuple[bool, str]:
    try:
        response = await client.put(f"/api/v1/admin/users/{user_id}/credits/set", headers=_get_auth_headers(), json={"amount": amount})
        response.raise_for_status()
        return True, response.json().get("message", "Success!")
    except httpx.HTTPStatusError as e: return False, await _handle_api_error(e)
    except httpx.RequestError as e: return False, str(e)

async def set_user_level(user_id: int, level: int) -> Tuple[bool, str]:
    try:
        response = await client.put(f"/api/v1/admin/users/{user_id}/level", headers=_get_auth_headers(), json={"level": level})
        response.raise_for_status()
        return True, response.json().get("message", "Success!")
    except httpx.HTTPStatusError as e: return False, await _handle_api_error(e)
    except httpx.RequestError as e: return False, str(e)

async def get_authorized_users() -> Optional[Set[int]]:
    try:
        response = await client.get("/api/v1/admin/auth/users", headers=_get_auth_headers())
        response.raise_for_status()
        return set(response.json())
    except (httpx.RequestError, httpx.HTTPStatusError): return None

async def add_authorized_user(user_id: int) -> Tuple[bool, str]:
    try:
        response = await client.post("/api/v1/admin/auth/users", headers=_get_auth_headers(), json={"user_id": user_id})
        response.raise_for_status()
        return True, response.json().get("message", "Success!")
    except httpx.HTTPStatusError as e: return False, await _handle_api_error(e)
    except httpx.RequestError as e: return False, str(e)

async def remove_authorized_user(user_id: int) -> Tuple[bool, str]:
    try:
        response = await client.delete(f"/api/v1/admin/auth/users/{user_id}", headers=_get_auth_headers())
        response.raise_for_status()
        return True, response.json().get("message", "Success!")
    except httpx.HTTPStatusError as e: return False, await _handle_api_error(e)
    except httpx.RequestError as e: return False, str(e)
