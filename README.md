# Ryuuko Bot v2.0.0

A modular, high-performance Discord bot ecosystem built on a service-oriented architecture. It features a powerful **Core API Service** that handles all AI and data logic, and a lightweight **Discord Client** for user interaction.

## Key Features

- **Service-Oriented Architecture**: The system is split into two distinct services:
  - **Core Service**: A standalone FastAPI backend that manages all business logic, database interactions (MongoDB), and communication with LLM providers.
  - **Discord Client**: A thin client focused solely on interacting with the Discord API and communicating with the Core Service.
- **Modular Provider System**: Easily switch between different LLM backends (e.g., Google's Gemini, custom proxies) via the Core Service.
- **Multimodal Conversations**: Supports contextual image analysis by allowing users to place images at specific points in their prompts.
- **Persistent, Multimodal Memory**: Conversation history, including both text and images, is stored for each user, enabling rich, contextual follow-up conversations.
- **User & Credit Management**: A robust system for managing authorized users, access levels, and credit balances, all handled by the Core Service.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- A MongoDB database instance

### Installation

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/zvwgvx/ryuuko-chatbot
    cd ryuuko
    ```

2.  **Set up a virtual environment:**
    ```sh
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install all dependencies:**
    Install both the Core Service and the Discord Bot client in editable mode.
    ```sh
    pip install -e ./packages/ryuuko-api
    pip install -e ./packages/discord-bot
    ```

### Configuration

You need to configure both services separately.

1.  **Core Service (`packages/core/.env`):**
    - Create a `.env` file from the `.env.example`.
    - Fill in `MONGODB_CONNECTION_STRING`, your LLM API keys, and a secure, private `CORE_API_KEY`.

2.  **Discord Bot (`packages/discord-bot/.env`):**
    - Create a `.env` file from the `.env.example`.
    - Fill in your `DISCORD_TOKEN` and the same `CORE_API_KEY` you set for the Core Service.

### Running the Ecosystem

You must run both services in separate terminals.

**➡️ Terminal 1: Start the Core Service**
```sh
# From the project root (ryuuko/)
python3 -m ryuuko-api
```

**⬅️ Terminal 2: Start the Discord Bot**
```sh
# From the project root (ryuuko/)
python3 -m discord-bot
```

## Commands

All commands are now handled by the Discord client, which communicates with the Core API. The available commands remain the same as in previous versions. Refer to `docs/COMMANDS.md` for a full list.

## Project Structure

-   `packages/`
    -   `core/`: The FastAPI Core Service.
    -   `discord-bot/`: The Discord client.
    -   `bot/`: (Legacy) The old monolithic bot, kept as a backup.
-   `docs/`: Detailed documentation for the project.
