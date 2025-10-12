# Development Notes

This document contains a collection of development notes, design decisions, and ideas for future improvements.

## Key Design Decisions

### 1. SDK Standardization (OpenAI SDK)

-   **Initial State**: The project initially used a mix of SDKs, including the native `google-genai` library for Gemini models.
-   **Decision**: To simplify the architecture and create a unified interface, all LLM providers were refactored to use the `openai` Python library.
-   **Implementation**: For Google Gemini models, requests are now directed to Google's OpenAI-compatible endpoint (`generativelanguage.googleapis.com/v1beta/openai/`). This allows us to use the same `AsyncOpenAI` client for multiple providers, streamlining the `llm_services/providers` code.

### 2. Multimodal Payload Structure

-   **Problem**: Early implementations mixed image data with user prompts in a non-standard way, leading to confusion for the model and high token counts.
-   **Decision**: Adopt a strict, OpenAI-compliant multimodal format for all user messages.
-   **Implementation (`events/messages.py`):
    -   The `content` of a user message is now **always** a list of parts.
    -   A user-defined placeholder (`[ảnh]`) is used to specify the exact position of images within the prompt.
    -   The `_build_multimodal_content` function parses the prompt, injects `image_url` parts at the correct locations, and constructs a clean, unambiguous payload.

### 3. Multimodal Conversation Memory

-   **Problem**: The memory store was previously only saving the text portion of user prompts, causing the bot to lose context in conversations involving images.
-   **Decision**: The entire multimodal `content` list (containing both text and image parts) is now saved to the memory store.
-   **Implementation (`storage/database.py`):
    -   The `add_message` function now stores the complete, structured payload.
    -   The token counting logic was upgraded to use `genai.count_tokens`, which can correctly calculate the token cost of complex, multimodal payloads, resolving `TypeError` exceptions.

### 4. Image Optimization and Token Management

-   **Problem**: Users sending high-resolution images resulted in excessively high token costs (e.g., 700k+ tokens for a single image).
-   **Decision**: Implement a mandatory image pre-processing step to optimize token usage while retaining sufficient detail.
-   **Implementation (`events/messages.py`):
    -   **Resizing**: Images are resized to fit within a `2048x2048` bounding box.
    -   **Format Conversion**: All images are converted to `JPEG` format, which is more efficient for tokenization than `PNG`.
    -   **Detail Parameter**: The `"detail": "auto"` parameter is included in the `image_url` payload, allowing the model to intelligently decide whether to use a low-cost or high-cost analysis mode based on the image size.

## Future Ideas & Potential Improvements

-   **True Function Calling**: The current implementation for `tools` only declares the functions to the model. A future improvement would be to implement a callback system where the bot can actually execute the `tool_calls` returned by the model (e.g., perform a search, run code) and send the results back to the model to generate a final answer.

-   **Streaming Tool Calls**: Enhance the `streamer` function in providers to parse and display `tool_calls` as they are being generated, rather than only at the end. This would provide a more interactive user experience.

-   **Web Dashboard**: A simple web-based dashboard (e.g., using FastAPI or Flask) could be built for bot owners to manage users, models, and credits, providing a more user-friendly alternative to Discord commands.

-   **Refined Memory Management**: The current token-based memory trimming is effective but could be improved. A more advanced strategy could summarize older parts of the conversation instead of simply discarding them.
