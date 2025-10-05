import asyncio
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
import httpx
from src.config import loader
from src.utils.ratelimit import get_rate_limiter

logger = logging.getLogger("Core.API.Client")

class UnifiedAPIClient:
    """Unified API client for all models"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.api_server = loader.API_SERVER
        self.api_key = loader.API_KEY
        self.timeout = loader.REQUEST_TIMEOUT

        # HTTP client configuration
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        self._initialized = True
        logger.info(f"Unified API client initialized: {self.api_server}")


# Global instances
client = UnifiedAPIClient()
rate_limiter = get_rate_limiter()

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

    # Extract system instructions
    system_instructions, filtered_messages = extract_system_instructions(messages)

    # Build config
    config = {
        "thinking_budget": thinking_budget,
        "temperature": temperature if temperature is not None else 1.1,
        "top_p": top_p if top_p is not None else 0.85,
        "tools": enable_tools
    }

    # Add optional parameters
    if top_k is not None:
        config["top_k"] = top_k
    if max_output_tokens is not None:
        config["max_output_tokens"] = max_output_tokens

    # Build the request payload (matches curl example format exactly)
    payload = {
        "provider": "polydevs",
        "model": model,
        "messages": filtered_messages,
        "config": config,
        "system_instruction": system_instructions if system_instructions else [""] # conflict
    }

    return payload

def is_thinking_model(model_name: str) -> bool:
    """Check if the model supports thinking (reasoning)"""
    return True

def is_model_available(model: str) -> Tuple[bool, str]:
    """Check if a model is available for use"""
    # For unified API, we assume all models are available
    # The API server will handle model availability
    return True, ""

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
    """Call the unified API"""
    try:
        # Apply rate limiting
        await rate_limiter.wait_if_needed(model)

        # Adjust thinking budget for thinking models
        if is_thinking_model(model) and thinking_budget == -1:
            thinking_budget = 25000
        elif not is_thinking_model(model):
            thinking_budget = -1

        # Build request payload
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

        # Log request for debugging
        logger.debug(f"API request for model {model}")
        logger.debug(f"Request payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

        # Make HTTP request
        async with httpx.AsyncClient(timeout=client.timeout) as http_client:
            response = await http_client.post(
                client.api_server,
                headers=client.headers,
                json=payload
            )

            # Log response details for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")

            response.raise_for_status()

            # Record successful request
            rate_limiter.record_request(model)

            # Get response text
            response_text = response.text
            logger.debug(f"Raw response (first 500 chars): {response_text[:500]}")

            # Check if response is empty
            if not response_text.strip():
                logger.error("API returned empty response")
                return False, "API server returned empty response"

            # Check content type
            content_type = response.headers.get("content-type", "").lower()

            # Handle JSON responses
            if "application/json" in content_type:
                try:
                    result = response.json()

                    # Extract content from JSON response
                    if isinstance(result, dict):
                        content = (
                                result.get("choices", [{}])[0].get("message", {}).get("content") or
                                result.get("content") or
                                result.get("text") or
                                result.get("response") or
                                result.get("data") or
                                result.get("output")
                        )

                        if content:
                            return True, str(content).strip()
                        else:
                            logger.error(f"No content found in JSON response")
                            return False, "No content found in API response"

                    elif isinstance(result, str):
                        return True, result.strip()

                    else:
                        return True, str(result).strip()

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    return False, f"API returned invalid JSON: {str(e)}"

            # Handle plain text responses
            else:
                logger.info(f"Received plain text response (content-type: {content_type})")

                # Check if it's HTML (error page)
                if response_text.strip().startswith("<"):
                    logger.error("Received HTML response (likely error page)")
                    return False, "API server returned HTML error page"

                # Treat as valid AI response content
                return True, response_text.strip()

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}"

        if e.response.status_code == 400:
            error_msg += " - Bad Request"
        elif e.response.status_code == 401:
            error_msg += " - Unauthorized (check API key)"
        elif e.response.status_code == 403:
            error_msg += " - Forbidden"
        elif e.response.status_code == 404:
            error_msg += " - Not Found"
        elif e.response.status_code == 429:
            error_msg += " - Rate Limited"
            # Handle rate limiting with retry
            retry_delay = await rate_limiter.handle_rate_limit_error(model, e)
            if retry_delay:
                await asyncio.sleep(retry_delay)
                return await call_unified_api(
                    messages, model, temperature, top_p, top_k,
                    max_output_tokens, enable_tools, thinking_budget
                )
        elif e.response.status_code >= 500:
            error_msg += " - Server Error"

        logger.error(f"HTTP error calling unified API: {error_msg}")
        return False, error_msg

    except httpx.RequestError as e:
        error_msg = f"Request error: {str(e)}"
        logger.error(f"Request error calling unified API: {error_msg}")
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(f"Error calling unified API: {error_msg}")
        return False, error_msg