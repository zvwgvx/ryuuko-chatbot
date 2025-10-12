# Project Architecture

This document provides a high-level overview of the Ryuuko Bot's architecture, its core components, and the flow of data through the system.

## Core Philosophy

The bot is designed with a modular and decoupled architecture. The goal is to separate concerns, making it easy to maintain, extend, and modify individual parts of the system without affecting others. For example, the LLM provider logic is completely separate from the Discord event handling logic.

## Data Flow: From Discord Message to AI Response

A typical interaction with the bot follows this sequence:

1.  **Message Reception (`events/messages.py`)**: A user sends a message mentioning the bot (`@Ryuuko`). The `on_message` event listener captures this message.

2.  **Request Queuing (`utils/request_queue.py`)**: To prevent rate-limiting and handle concurrent requests gracefully, the incoming message is not processed immediately. Instead, it's added to an asynchronous queue (`RequestQueue`). A background worker processes requests from this queue one by one.

3.  **Request Processing (`events/messages.py`)**: The `process_ai_request` function is called for the request.
    - It fetches the user's configuration (preferred model, access level) from the `UserConfigManager`.
    - It processes any attachments (images), resizing and optimizing them for the API.
    - It retrieves the user's conversation history from the `MemoryStore`.
    - It constructs a multimodal payload compliant with the OpenAI Chat Completions API standard.

4.  **API Gateway (`llm_services/api_client.py`)**: The constructed payload is sent to the `call_unified_api` method. This acts as a central gateway.
    - It identifies the correct provider (e.g., `polydevs`, `aistudio`) based on the user's chosen model.
    - It retrieves the appropriate API key from the environment.
    - It forwards the request to the designated provider module.

5.  **LLM Provider (`llm_services/providers/*.py`)**: The specific provider module takes over.
    - It adds provider-specific context (like system instructions for `polydevs` models) and the current timestamp to the system prompt.
    - It initializes an `AsyncOpenAI` client with the correct `base_url` and API key.
    - It makes the final streaming API call to the LLM backend.

6.  **Streaming Response**: The provider streams the response back through the gateway to `events/messages.py`.

7.  **Response Delivery & Memory Update**: 
    - The final response is sent back to the user on Discord.
    - The user's prompt (including images) and the assistant's response are saved back to the `MemoryStore` to maintain conversation context.
    - Token usage is calculated and logged.

## Directory Structure

-   `src/`
    -   `commands/`: Contains the definitions for all user-facing and admin-facing bot commands (e.g., `.model`, `.memory`).
    -   `config/`: Manages the loading of all configurations. It loads the main `.env` file and provides access to settings from `config.json` and `instructions.json`.
    -   `events/`: Home to the core event listeners, primarily `on_message`, which is the entry point for all conversations.
    -   `llm_services/`: The heart of the AI gateway.
        -   `api_client.py`: The central router that directs requests to the correct provider.
        -   `providers/`: Individual modules for each LLM backend. Each provider is responsible for adapting the standard payload to its specific API requirements.
    -   `storage/`: Manages data persistence.
        -   `database.py`: Handles all interactions with MongoDB, including user profiles, model configurations, and conversation memory.
        -   `memory.py`: An in-memory cache layer for conversation history to reduce database lookups (though currently, it interfaces directly with `database.py`).
    -   `utils/`: Contains utility classes and functions, such as the `RequestQueue`.
-   `config/`: Contains static, non-sensitive configuration files like `config.json` (for bot settings) and `instructions.json` (for provider-specific system prompts).
