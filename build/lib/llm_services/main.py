# src/llm_services/main.py
import logging
from typing import Dict, Any, Tuple
from fastapi.responses import JSONResponse
import json

from src.config import loader
from src.llm_services.providers import get_provider_forward

logger = logging.getLogger("Gateway.Logic")

def _normalize_request_payload(data: Dict[str, Any]) -> None:
    """
    Normalizes/validates client-sent fields like config and system_instruction.
    This function mutates the input dictionary `data`.
    """
    if not isinstance(data, dict):
        return

    cfg = data.get("config", {}) or {}
    if not isinstance(cfg, dict): cfg = {}

    # Normalize values with defaults
    temp = float(cfg.get("temperature", 0.7))
    top_p = float(cfg.get("top_p", 1.0))
    tools = str(cfg.get("tools", "false")).lower() in ("true", "1", "yes")
    tb = int(cfg.get("thinking_budget", -1))

    # Clamp values within valid ranges
    temp = max(0.0, min(2.0, temp))
    top_p = max(0.0, min(1.0, top_p))
    if tb != -1:
        tb = max(0, min(24576, tb))

    data["config"] = {"temperature": temp, "top_p": top_p, "tools": tools, "thinking_budget": tb}

    sys_ins = data.get("system_instruction", [])
    if isinstance(sys_ins, str):
        sys_list = [sys_ins] if sys_ins.strip() else []
    elif isinstance(sys_ins, list):
        sys_list = [str(s).strip() for s in sys_ins if isinstance(s, str) and s.strip()]
    else:
        sys_list = []
    data["system_instruction"] = sys_list


async def handle_proxy_request(payload: Dict[str, Any]) -> Tuple[bool, Any]:
    """
    Core logic for processing an AI request. Can be called directly by the bot.
    """
    try:
        # 1. Determine Provider
        provider = payload.get("provider", "").strip().lower()
        if not provider or provider not in loader.ALLOWED_PROVIDERS:
            return False, f"Provider '{provider}' not specified or not supported."

        # 2. Determine Model
        model = payload.get("model", "").strip() or loader.PROVIDER_DEFAULT_MODEL.get(provider)
        if not model: return False, f"No model specified or default for provider '{provider}'."

        allowed_models = loader.PROVIDER_ALLOWED_MODELS.get(provider, set())
        if allowed_models and model not in allowed_models:
            return False, f"Model '{model}' is not allowed for provider '{provider}'."
        payload["model"] = model

        # --- CORE FIX for Lỗi 3: Simplified and corrected API Key lookup ---
        # 3. Get Upstream API Key directly by provider name
        upstream_api_key = loader.UPSTREAM_API_KEYS.get(provider)
        if not upstream_api_key:
            return False, f"API key for provider '{provider}' is not configured on the server."
        # ------------------------------------------------------------------

        # 4. Get the forwarding function for the provider
        forward_fn = get_provider_forward(provider)
        if not forward_fn: return False, f"Provider '{provider}' is not implemented."

        # 5. Normalize payload
        _normalize_request_payload(payload)

        # 6. Call the provider's forwarding function
        # The forward function expects (request, data, api_key).
        # Since this is an internal call, we pass None for the FastAPI request object.
        # The payload becomes the 'data' argument.
        response = await forward_fn(None, payload, upstream_api_key)

        # 7. Process the response
        # The response can be a StreamingResponse or a JSONResponse.
        # We need to consume the body differently for each.
        full_body_bytes = b""
        if hasattr(response, "body"):  # For JSONResponse (errors)
            full_body_bytes = response.body
        elif hasattr(response, "body_iterator"):  # For StreamingResponse (success)
            async for chunk in response.body_iterator:
                full_body_bytes += chunk

        full_body_str = full_body_bytes.decode("utf-8", errors="ignore")

        if not (200 <= response.status_code < 300):
            logger.error(f"Error from '{provider}' (Status {response.status_code}): {full_body_str}")
            return False, f"API Error from {provider}: {full_body_str}"

        # For successful streaming responses, the content is plain text, not JSON.
        # For successful JSON responses, we need to parse it.
        try: return True, json.loads(full_body_str)
        except json.JSONDecodeError: return True, {"text": full_body_str}

    except Exception as e:
        logger.exception(f"Unexpected error in ai_services logic: {e}")
        return False, f"An internal error occurred in the ai_services: {str(e)}"
