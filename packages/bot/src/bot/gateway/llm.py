# src/bot/api/client.py
import json
import logging
from typing import List, Dict, Any, Tuple, Optional

# --- CORE CHANGE: Import llm_services logic directly instead of httpx ---
from src.llm_services.main import handle_proxy_request
# -------------------------------------------------------------------

from src.utils.ratelimit import get_rate_limiter

logger = logging.getLogger("Bot.API.Client")

# Global instances
rate_limiter = get_rate_limiter()

# Helper functions (these are still useful and can be kept)
def extract_system_instructions(messages: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Extract system instructions from messages and return them separately"""
    system_instructions = []
    filtered_messages = []
    for msg in messages:
        if msg.get("role") == "system":
            content = msg.get("content", "")
            if content:
                system_instructions.append(content)
        else:
            filtered_messages.append(msg)
    return system_instructions, filtered_messages

def build_api_request(
        messages: List[Dict[str, Any]],
        model: str,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        enable_tools: bool = True,
        thinking_budget: int = None
) -> Dict[str, Any]:
    """Build request payload for the unified API"""
    system_instructions, filtered_messages = extract_system_instructions(messages)

    config = {
        "thinking_budget": thinking_budget,
        "temperature": temperature if temperature is not None else 1.1,
        "top_p": top_p if top_p is not None else 0.85,
        "tools": enable_tools
    }
    if top_k is not None: config["top_k"] = top_k
    if max_output_tokens is not None: config["max_output_tokens"] = max_output_tokens

    # The provider is now selected based on the model by the llm_services logic,
    # but we can provide a default. Let's assume 'polydevs' is the primary.
    payload = {
        "provider": "polydevs", # Or determine this dynamically
        "model": model,
        "messages": filtered_messages,
        "config": config,
        "system_instruction": system_instructions
    }
    return payload

from src.storage.database import MongoDBStore


def is_model_available(model: str, db_store: MongoDBStore) -> Tuple[bool, str]:
    """Check if a model is available in the database."""
    if db_store.model_exists(model):
        return True, ""

    supported_models = db_store.get_supported_models()
    if not supported_models:
        return False, "There are no models configured in the system."

    return False, f"Model `{model}` is not available. Please choose from: `{'`, `'.join(supported_models)}`"

# --- REWRITTEN CORE FUNCTION ---
async def call_unified_api(
        messages: List[Dict[str, Any]],
        model: str,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        enable_tools: bool = True,
        thinking_budget: int = -1
) -> Tuple[bool, str]:
    """
    Calls the integrated AI Gateway logic directly as a Python function.
    """
    try:
        await rate_limiter.wait_if_needed(model)

        # Adjust thinking budget (this logic remains the same)
        is_thinking = True # Assuming all models support this for now
        if is_thinking and thinking_budget == -1:
            thinking_budget = 25000
        elif not is_thinking:
            thinking_budget = -1

        # Build the request payload dictionary
        payload = build_api_request(
            messages=messages,
            model=model,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens,
            enable_tools=enable_tools,
            thinking_budget=thinking_budget
        )
        logger.debug(f"Calling ai_services logic with payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

        # --- CORE CHANGE: Call the function directly ---
        success, result = await handle_proxy_request(payload)
        # ---------------------------------------------

        if not success:
            logger.error(f"Gateway logic returned an error: {result}")
            return False, str(result)

        # If successful, 'result' is the JSON body from the provider's response
        # We need to extract the actual text content from it.
        if isinstance(result, dict):
            # This is a flexible way to find the content in various response formats
            content = (
                result.get("choices", [{}])[0].get("message", {}).get("content") or
                result.get("content", [{}])[0].get("text") or # Gemini format
                result.get("content") or
                result.get("text") or
                result.get("response")
            )
            if content:
                rate_limiter.record_request(model)
                return True, str(content).strip()
            else:
                logger.error(f"No content found in successful API response: {result}")
                return False, "API returned a valid response, but no text content was found."
        else:
             # If the result is not a dict, it might be an error message we missed
            logger.error(f"Gateway returned an unexpected format: {result}")
            return False, f"Unexpected response format from ai_services: {type(result)}"

    except Exception as e:
        error_msg = f"Unexpected error in API client: {str(e)}"
        logger.exception(error_msg)
        return False, error_msg