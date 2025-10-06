# Ryuuko — Discord LLM Bot

**Ryuuko** is a modular and extensible Discord bot powered by Large Language Models (LLMs). It's designed to be a versatile chatbot that can be customized and extended with new commands and functionalities.

## Features

*   **Modular Architecture**: Easily extend the bot by adding new commands, events, or services.
*   **LLM Integration**: Connects with LLM providers for intelligent conversation.
*   **Conversation Memory**: Remembers previous messages in a conversation for better context.
*   **Configuration Management**: Flexible configuration system using environment variables and a `config.json` file.
*   **Role-Based Access Control**: Restrict commands to authorized users.
*   **Asynchronous Processing**: Uses a request queue to handle LLM API calls without blocking the bot.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Python 3.10+
*   MongoDB server
*   A Discord Bot Token

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/zvwgvx/ryuuko-chatbot.git
    cd ryuuko-chatbot
    ```

2.  **Install dependencies:**
    ```bash
    # Install main dependencies
    pip install .

    # To install testing dependencies as well
    pip install .[test]
    ```

3.  **Configure the bot:**
    *   Create a `.env` file in the root directory and add your secrets. For a full list of required API keys, see the [Setup Guide](docs/SETUP.md).
        ```env
        # Discord and Database
        DISCORD_TOKEN="your_discord_bot_token"
        MONGODB_CONNECTION_STRING="your_mongodb_connection_string"

        # LLM API Keys (only add the ones you use)
        AISTUDIO_API_KEY="your_aistudio_api_key"
        POLYDEVS_API_KEY="your_polydevs_api_key"
        PROXYVN_API_KEY="your_proxyvn_api_key"

    *   Modify `config.json` for additional settings if needed.

## Usage

To run the bot, use one of the following commands:

```bash
# Using the python module directly
python -m src

# Using the installed script
start
```

Once the bot is running, you can interact with it on Discord using the `.` prefix. For a full list of commands, see the [Commands Reference](docs/COMMANDS.md).

## Documentation

For more detailed information, please refer to the following documents:

*   [**Architecture**](docs/ARCHITECTURE.md): An overview of the project's technical design.
*   [**Setup Guide**](docs/SETUP.md): Detailed setup and configuration instructions.
*   [**Command Reference**](docs/COMMANDS.md): A complete list of all available bot commands.
*   [**Deployment Guide**](docs/DEPLOYMENT.md): Instructions for deploying the bot to a production environment.

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) to get started.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.