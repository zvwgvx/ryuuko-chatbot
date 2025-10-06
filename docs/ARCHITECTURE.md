# Architecture

This document provides a detailed overview of the Ryuuko Discord Bot's architecture.

## Overview

The bot is built with a modular architecture that separates concerns into distinct components, making it easy to maintain and extend. The core components are the `Bot` instance, `Commands`, `Events`, and `Services`. The system is designed to be asynchronous, using a request queue to handle long-running LLM API calls without blocking the main event loop.

## Directory Structure

The project is organized into the following directories:

```
├── config/           # Configuration files and loaders
├── docs/             # Project documentation
├── logs/             # Log files
├── scripts/          # Utility scripts
├── src/              # Source code
│   ├── bot/          # Core bot logic, commands, and events
│   ├── config/       # Configuration loading and management
│   ├── llm_services/ # LLM API integration
│   ├── storage/      # Database and memory storage
│   ├── utils/        # Helper functions and utilities
│   ├── __main__.py   # Main application entry point
├── tests/            # Unit and integration tests
├── .env              # Environment variables (not version controlled)
├── config.json       # Main configuration file
├── requirements.txt  # Python dependencies
└── main.py           # Script to run the bot module
```

## Core Components

### 1. Bot (`src/bot/main.py`)

The `Bot` class is the central component of the application. It inherits from `discord.ext.commands.Bot` and is responsible for:
- Initializing the Discord client and connecting to the gateway.
- Registering commands and event handlers.
- Managing dependencies and injecting them into other modules.
- Handling global command errors.

### 2. Commands (`src/bot/commands/`)

Commands are organized into separate files based on their functionality (e.g., `admin.py`, `user.py`). The `register_all_commands` function dynamically loads all commands and attaches them to the bot instance. This modular approach allows for easy addition of new commands without modifying the core bot file.

### 3. Events (`src/bot/events/`)

Event handlers (e.g., `on_message`) are also organized into separate files. The `register_all_events` function loads and registers these handlers with the bot. This keeps event-related logic separate from the main bot file.

### 4. Services

Services provide specific functionalities that can be shared across different parts of the application.

-   **Authentication Service (`src/bot/services/auth.py`)**: Manages user authorization, controlling which users can execute restricted commands.
-   **LLM Services (`src/llm_services/`)**: This component is responsible for interacting with Large Language Models. It abstracts the API calls, allowing the bot to support different LLM providers.

### 5. Storage (`src/storage/`)

The storage layer handles data persistence.
-   **`MongoDBStore`**: Interacts with a MongoDB database to store conversation history, authorized users, and other persistent data.
-   **`MemoryStore`**: An in-memory cache for conversation history to provide faster access and reduce database queries.

## Configuration (`src/config/`)

Configuration is managed through a combination of a `.env` file for secrets and a `config.json` file for non-sensitive settings. The `loader.py` module loads these configurations and makes them available throughout the application.

## Data Flow (On Message Event)

1.  A user sends a message in a Discord channel.
2.  The `on_message` event handler in `src/bot/events/chat.py` is triggered.
3.  The handler checks if the message should be processed (e.g., not from a bot, in a valid channel).
4.  The message is added to a request queue (`src/utils/queue.py`) for processing.
5.  A background task picks up the request from the queue.
6.  The `MemoryStore` retrieves the recent conversation history for the user.
7.  The `llm_services` component sends the conversation history to the LLM API.
8.  The LLM API returns a response.
9.  The bot sends the response back to the Discord channel.
10. The new message and response are saved to the `MemoryStore` and `MongoDBStore`.

## Error Handling

Global command error handling is implemented in `src/bot/main.py`. The `on_command_error` event handler catches common errors like `CommandNotFound`, `CheckFailure`, and `MissingRequiredArgument`, providing user-friendly feedback and logging unexpected exceptions.