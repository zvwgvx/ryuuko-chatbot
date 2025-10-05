# src/gateway/logic.py
import logging
from typing import Dict, Any, Tuple
from fastapi.responses import JSONResponse
import json

from src.config import loader
from src.gateway.providers import get_provider_forward

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

    Args:
        payload (Dict[str, Any]): The request data, same format as sent to the API.

    Returns:
        Tuple[bool, Any]: A tuple of (success, result).
                          If success is True, result is the AI's response content (dict or str).
                          If success is False, result is an error message (str).
    """
    try:
        # 1. Determine Provider
        provider = payload.get("provider", "").strip().lower()
        if not provider or provider not in loader.ALLOWED_PROVIDERS:
            return False, f"Provider '{provider}' not specified or not supported."

        # 2. Determine Model
        model = payload.get("model", "").strip()
        if not model:
            model = loader.PROVIDER_DEFAULT_MODEL.get(provider)
        if not model:
             return False, f"No model specified and no default model for provider '{provider}'."

        allowed_models = loader.PROVIDER_ALLOWED_MODELS.get(provider, set())
        if allowed_models and model not in allowed_models:
            return False, f"Model '{model}' is not allowed for provider '{provider}'."
        payload["model"] = model # Ensure model is in payload

        # 3. Get Upstream API Key
        # This part needs to map provider names to env var names defined in config
        # Assuming a simple mapping for now. Example: 'openai' -> 'OPENAI_API_KEY'
        key_name = provider.upper() + "_API_KEY"
        upstream_api_key = loader.UPSTREAM_API_KEYS.get(key_name)
        if provider == "aistudio" and not upstream_api_key: # Special fallback for aistudio/gemini
             upstream_api_key = loader.UPSTREAM_API_KEYS.get("GEMINI_API_KEY")

        if not upstream_api_key:
            return False, f"API key for provider '{provider}' is not configured on the server."

        # 4. Get the forwarding function for the provider
        forward_fn = get_provider_forward(provider)
        if not forward_fn:
            return False, f"Provider '{provider}' is not implemented."

        # 5. Normalize payload
        _normalize_request_payload(payload)

        # 6. Call the provider's forwarding function
        # The forward_fn is expected to return a FastAPI Response object
        response: JSONResponse = await forward_fn(payload, upstream_api_key)

        # 7. Process the response
        if 200 <= response.status_code < 300:
            # Success
            response_body = json.loads(response.body.decode("utf-8"))
            return True, response_body
        else:
            # Error
            try:
                error_body = json.loads(response.body.decode("utf-8"))
                error_message = error_body.get("error", "Unknown error from provider.")
            except:
                error_message = response.body.decode("utf-8", errors="ignore")
            logger.error(f"Error from provider '{provider}' (Status {response.status_code}): {error_message}")
            return False, f"API Error from {provider}: {error_message}"

    except Exception as e:
        logger.exception(f"Unexpected error in gateway logic: {e}")
        return False, f"An internal error occurred in the gateway: {str(e)}"