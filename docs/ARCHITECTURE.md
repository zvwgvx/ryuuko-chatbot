# Architecture v2.0.0

This document provides a detailed overview of the Ryuuko Bot v2.0.0 ecosystem, which is built on a **service-oriented architecture**.

## Core Philosophy

The project was refactored from a monolithic application into a decoupled, two-part system. This design enhances scalability, maintainability, and allows for the future addition of new clients (e.g., a Telegram bot, a web UI) without modifying the core logic.

## System Components

### 1. Core Service (`packages/core`)

This is the centralized "brain" of the entire ecosystem. It is a standalone **FastAPI** application responsible for all heavy lifting and business logic.

-   **Responsibilities**:
    -   **AI Processing**: Manages all interactions with third-party LLM providers (Google Gemini, ProxyVN, etc.).
    -   **Data Persistence**: Acts as the sole interface to the MongoDB database. It handles all data operations related to user configurations, conversation memory, supported models, and authorization.
    -   **Business Logic**: Contains all rules for user access, credit management, and conversation history trimming.
    -   **API Provision**: Exposes a secure, RESTful API for clients to consume.

-   **Key Technologies**: FastAPI, Pydantic, MongoDB (via Pymongo), OpenAI SDK.

### 2. Discord Bot (`packages/discord-bot`)

This is a lightweight "thin client" responsible for all interactions with the Discord platform.

-   **Responsibilities**:
    -   **Discord Gateway**: Connects to Discord, listens for events (`on_message`), and handles command parsing.
    -   **User Interaction**: Receives messages and commands from users.
    -   **Payload Construction**: Processes user input and file attachments (images) into a standardized, multimodal payload.
    -   **API Communication**: Acts as an HTTP client (using `httpx`) that sends requests to the Core Service API.
    -   **Response Presentation**: Receives streamed responses from the Core Service and displays them back to the user in Discord.

-   **Key Technologies**: discord.py, httpx, Pillow.

## Data Flow: From Discord Message to AI Response

A typical interaction follows this sequence:

1.  **Message Reception (Discord Bot)**: The `on_message` event listener in `discord-bot` captures a user's message.

2.  **Request Queuing (Discord Bot)**: The request is placed into an asynchronous queue (`RequestQueue`) to be processed sequentially.

3.  **Payload Creation (Discord Bot)**: The `process_ai_request` function:
    -   Processes any image attachments, resizing and encoding them into base64 `data URI` format.
    -   Constructs a multimodal `content` list following the OpenAI API standard.
    -   Builds a final JSON payload containing the `user_id` and the `messages` list.

4.  **API Call (Discord Bot -> Core Service)**: The `api_client` sends a `POST` request with the payload to the `/api/v1/chat/completions` endpoint of the Core Service, including the `CORE_API_KEY` for authentication.

5.  **Request Handling (Core Service)**: The `chat_completions` endpoint in `main.py`:
    -   Verifies the `CORE_API_KEY`.
    -   Fetches the user's full conversation history and configuration from `MongoDBStore`.
    -   Constructs the final, complete list of messages to be sent to the LLM.
    -   Determines the correct LLM provider based on the model name.
    -   Calls the appropriate `forward` function in the `providers/` directory.

6.  **LLM Interaction (Core Service)**: The provider module communicates with the external LLM API and streams the response back.

7.  **Database Update (Core Service)**: After the full response is received, the Core Service saves the user's prompt and the final AI response to the database.

8.  **Response Streaming (Core Service -> Discord Bot -> Discord)**: The response is streamed back through the API to the Discord client, which then edits its message in real-time to display the generated text to the user.
