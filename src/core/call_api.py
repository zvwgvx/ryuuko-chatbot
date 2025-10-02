import asyncio
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
import httpx
from src.config import loader
from ..utils.rate_limiter import get_rate_limiter

logger = logging.getLogger("Call API")


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


def has_vision_content(messages: List[Dict[str, Any]]) -> bool:
    """Check if messages contain vision/image content"""
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    return True
    return False


def count_vision_content(messages: List[Dict[str, Any]]) -> int:
    """Count number of images in messages"""
    count = 0
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    count += 1
    return count


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
            # Keep the message as-is, including vision content
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
        thinking_budget: int = 25000
) -> Dict[str, Any]:
    """Build request payload for the unified API"""

    # Extract system instructions
    system_instructions, filtered_messages = extract_system_instructions(messages)

    # Check for vision content
    has_vision = has_vision_content(filtered_messages)
    vision_count = count_vision_content(filtered_messages)

    if has_vision:
        logger.info(f"🖼️ Building request with {vision_count} image(s)")

        # Log structure of vision messages (without full base64)
        for i, msg in enumerate(filtered_messages):
            if isinstance(msg.get("content"), list):
                parts_info = []
                for part in msg["content"]:
                    if part.get("type") == "text":
                        parts_info.append(f"text({len(part.get('text', ''))} chars)")
                    elif part.get("type") == "image_url":
                        url = part.get("image_url", {}).get("url", "")
                        if url.startswith("data:"):
                            mime = url.split(";")[0].replace("data:", "")
                            parts_info.append(f"image({mime})")
                logger.info(f"  Message {i}: [{', '.join(parts_info)}]")

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

    # Add vision flag if needed
    if has_vision:
        config["vision"] = True

    # Build the request payload
    payload = {
        "provider": "polydevs",
        "model": model,
        "messages": filtered_messages,
        "config": config,
        "system_instruction": system_instructions if system_instructions else [""]
    }

    return payload


def is_thinking_model(model_name: str) -> bool:
    """Check if the model supports thinking (reasoning)"""
    thinking_patterns = [
        "thinking",
        "reasoning",
        "o3-mini",
        "o1"
    ]

    model_lower = model_name.lower()
    return any(pattern in model_lower for pattern in thinking_patterns)


def is_model_available(model: str) -> Tuple[bool, str]:
    """Check if a model is available for use"""
    # For unified API, we assume all models are available
    # The API server will handle model availability
    return True, ""


def sanitize_payload_for_logging(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a sanitized copy of payload for logging (truncate base64 images)"""
    import copy
    sanitized = copy.deepcopy(payload)

    for msg in sanitized.get("messages", []):
        content = msg.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    url = part.get("image_url", {}).get("url", "")
                    if url.startswith("data:") and len(url) > 100:
                        # Truncate base64 for logging
                        mime_part = url.split(";base64,")[0]
                        part["image_url"]["url"] = f"{mime_part};base64,[BASE64_DATA_TRUNCATED_{len(url)}_BYTES]"

    return sanitized


async def call_api(
        messages: List[Dict[str, Any]],
        model: str = "ryuuko-r1-eng-mini",
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        enable_tools: bool = True,
        thinking_budget: int = -1
) -> Tuple[bool, str]:
    """
    Main API call function - calls unified polydevs API
    Returns: (success: bool, response: str)
    """
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

        # Check if this is a vision request
        has_vision = has_vision_content(messages)
        vision_count = count_vision_content(messages)

        # Log request for debugging
        logger.info(f"📤 API request for model: {model}" + (f" with {vision_count} image(s)" if has_vision else ""))

        # Log sanitized payload (with truncated images)
        sanitized = sanitize_payload_for_logging(payload)
        logger.debug(f"Request payload structure: {json.dumps(sanitized, indent=2, ensure_ascii=False)}")

        # Log actual payload size
        payload_json = json.dumps(payload)
        payload_size = len(payload_json)
        logger.info(f"Payload size: {payload_size:,} bytes ({payload_size / 1024:.2f} KB)")

        # Make HTTP request
        async with httpx.AsyncClient(timeout=client.timeout) as http_client:
            response = await http_client.post(
                client.api_server,
                headers=client.headers,
                json=payload
            )

            # Log response details
            logger.info(f"📥 Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")

            # Check for specific vision-related errors
            if response.status_code >= 400:
                error_body = response.text[:1000]
                logger.error(f"API error response: {error_body}")

                # Check for vision-related error messages
                error_lower = error_body.lower()
                if any(keyword in error_lower for keyword in ["vision", "image", "multimodal", "base64", "media"]):
                    logger.error("⚠️ Vision-related error detected!")
                    if has_vision:
                        return False, f"Vision not supported by this model/API: {error_body[:200]}"

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
                            logger.info(f"✅ Successfully received response ({len(str(content))} chars)")
                            if has_vision:
                                logger.info(f"🖼️ Vision request successful!")
                            return True, str(content).strip()
                        else:
                            logger.error(f"No content found in JSON response: {result}")
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
        error_body = e.response.text[:500] if hasattr(e.response, 'text') else ""

        if e.response.status_code == 400:
            error_msg += " - Bad Request"
            logger.error(f"Bad Request body: {error_body}")

            # Check if it's a vision-related 400 error
            if has_vision and any(kw in error_body.lower() for kw in ["image", "vision", "multimodal", "base64"]):
                error_msg += " (Vision content may not be supported by this model)"

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
                return await call_api(
                    messages, model, temperature, top_p, top_k,
                    max_output_tokens, enable_tools, thinking_budget
                )
        elif e.response.status_code >= 500:
            error_msg += " - Server Error"

        logger.error(f"HTTP error calling unified API: {error_msg}")
        if has_vision:
            logger.error(f"⚠️ This error occurred with a vision request ({vision_count} images)")

        return False, f"{error_msg}\n{error_body[:200]}" if error_body else error_msg

    except httpx.RequestError as e:
        error_msg = f"Request error: {str(e)}"
        logger.error(f"Request error calling unified API: {error_msg}")
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(f"Error calling unified API: {error_msg}")
        return False, error_msg