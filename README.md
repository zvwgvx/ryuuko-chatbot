# Ryuuko Bot

A modular, high-performance Discord bot designed as a gateway to various Large Language Models (LLMs). It supports multimodal interactions, conversation memory, and a robust user management system.

## Key Features

- **Modular Provider System**: Easily switch between different LLM backends (e.g., Google's Gemini, custom proxies like ProxyVN) without changing the core logic.
- **Multimodal Conversations**: Supports understanding and discussing images within a conversation. Users can place images at specific points in their prompt for contextual analysis.
- **Persistent Memory**: Maintains conversation history for each user, allowing for follow-up questions and contextual continuity.
- **User & Credit Management**: Features a built-in system for managing authorized users, access levels, and credit balances, all stored in MongoDB.
- **Optimized for Performance**: Includes features like asynchronous request queuing and image processing to ensure responsiveness.
- **Secure Configuration**: Manages all sensitive keys and credentials through a `.env` file, keeping them out of the codebase.
- **Rich Command Set**: Provides a comprehensive suite of commands for both users and bot owners.

## Getting Started

Follow these instructions to get a local copy up and running.

### Prerequisites

- Python 3.11 or higher
- Git
- A MongoDB database instance (local or cloud-hosted)

### Installation

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/zvwgvx/ryuuko-chatbot.git
    cd ryuuko
    ```

2.  **Set up a virtual environment:**
    ```sh
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    The project uses `pyproject.toml`. Install the bot in editable mode, which will also install all required dependencies.
    ```sh
    pip install -e ./packages/bot
    ```

4.  **Configure the bot:**
    - Navigate to the `packages/bot` directory.
    - Create a file named `.env` by copying the example:
      ```sh
      cp .env.example .env
      ```
    - Open the `.env` file and fill in your credentials:
      ```ini
      # Your Discord Bot Token
      DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN"

      # Connection string for your MongoDB database
      MONGODB_CONNECTION_STRING="mongodb://user:pass@host:port/"

      # --- API Keys for LLM Providers ---
      # At least one is required for the bot to function
      GEMINI_API_KEY="YOUR_GOOGLE_AI_STUDIO_API_KEY"
      POLYDEVS_API_KEY="YOUR_POLYDEVS_API_KEY"
      PROXYVN_API_KEY="YOUR_PROXYVN_API_KEY"
      ```

5.  **Set up configuration files:**
    - In the `packages/bot/config/` directory, review and customize `config.json` and `instructions.json` as needed.

### Running the Bot

From the project root directory (`ryuuko`), run the bot as a module:

```sh
python3 -m bot
```

## Commands

### User Commands

| Command               | Description                                      |
| --------------------- | ------------------------------------------------ |
| `.ping`               | Checks the bot's latency.                        |
| `.help`               | Displays the list of available commands.         |
| `.model <model_name>` | Sets your preferred AI model.                    |
| `.profile [user]`     | Shows your (or another user's) profile.          |
| `.models`             | Lists all available AI models.                   |
| `.clearmemory`        | Clears your personal conversation history.       |

### Admin & Owner Commands

| Command                         | Description                                      |
| ------------------------------- | ------------------------------------------------ |
| `.memory [user]`                | Inspects a user's conversation memory.           |
| `.auth <user>`                  | Authorizes a user to use the bot.                |
| `.deauth <user>`                | De-authorizes a user.                            |
| `.auths`                        | Lists all authorized users.                      |
| `.addmodel <name> <cost> <lvl>` | Adds a new supported model to the database.      |
| `.removemodel <name>`           | Removes a model.                                 |
| `.editmodel <name> <cost> <lvl>`| Edits an existing model's properties.            |
| `.addcredit <user> <amount>`    | Adds credits to a user.                          |
| `.setcredit <user> <amount>`    | Sets a user's credit balance.                    |
| `.setlevel <user> <level>`      | Sets a user's access level.                      |

## Project Structure

- `packages/bot/src/`: Main source code for the bot.
  - `commands/`: Handles command definitions.
  - `config/`: Manages loading of configurations.
  - `events/`: Contains event listeners (e.g., `on_message`).
  - `llm_services/`: Core logic for the LLM gateway and providers.
  - `storage/`: Manages conversation memory and database interactions.
- `packages/bot/config/`: Bot-specific configuration files (`config.json`, `instructions.json`).
- `pyproject.toml`: Project metadata and dependencies.

## Contributing

Contributions are welcome! Please feel free to fork the repository, make changes, and submit a pull request.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## License

This project is distributed under the MIT License. See `LICENSE` for more information.
