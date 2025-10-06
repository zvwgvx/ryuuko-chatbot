# Setup Guide

This guide provides detailed instructions for setting up the Ryuuko Discord Bot for development and testing.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

-   **Python 3.10 or higher**: You can download it from the [official Python website](https://www.python.org/downloads/).
-   **Git**: For cloning the repository.
-   **MongoDB**: A running MongoDB instance is required for data storage. You can use a local installation or a cloud-based service like MongoDB Atlas.

## Installation Steps

1.  **Clone the Repository**

    Open your terminal and clone the repository from GitHub:
    ```bash
    git clone https://github.com/your-github-username/your-repository-name.git
    cd your-repository-name
    ```

2.  **Create a Virtual Environment**

    It is highly recommended to use a virtual environment to manage project dependencies.
    ```bash
    # Create the virtual environment
    python -m venv venv

    # Activate the virtual environment
    # On Windows
    venv\\Scripts\\activate
    # On macOS and Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies**

    With your virtual environment activated, install the required Python packages using pip:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

The bot's configuration is managed through a combination of a `.env` file for sensitive data and a `config.json` file for general settings.

1.  **Create the `.env` File**

    Create a file named `.env` in the root directory of the project. This file is used to store your secret keys and is ignored by Git.

    ```
    touch .env
    ```

2.  **Add Environment Variables**

    Open the `.env` file and add the following required variables:

    ```env
    # Your Discord bot token from the Discord Developer Portal
    DISCORD_TOKEN="your_discord_bot_token_here"

    # The connection string for your MongoDB database
    MONGODB_CONNECTION_STRING="mongodb://user:password@host:port/"
    ```

    Replace the placeholder values with your actual credentials.

3.  **Review `config.json`**

    The `config.json` file in the root directory contains non-sensitive configuration options. You can modify these values to change the bot's behavior.

    ```json
    {
      "USE_MONGODB": true,
      "MONGODB_DATABASE_NAME": "polydevsdb",
      "REQUEST_TIMEOUT": 100,
      "MAX_MSG": 1900,
      "MEMORY_MAX_PER_USER": 100,
      "MEMORY_MAX_TOKENS": 10000
    }
    ```

## Running the Bot

Once you have completed the installation and configuration, you can run the bot with the following command:

```bash
python -m src
```

If everything is configured correctly, you will see log messages in your terminal indicating that the bot has successfully connected to Discord. You can then invite the bot to your server and start interacting with it.