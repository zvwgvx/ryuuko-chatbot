# Detailed Setup Guide

This guide provides a step-by-step walkthrough for setting up the Ryuuko Bot for development and local testing.

## Step 1: System Prerequisites

Before you begin, ensure your system has the following software installed:

-   **Python**: Version 3.11 or higher is required. You can check your version with `python3 --version`.
-   **Git**: Required for cloning the repository. You can check your version with `git --version`.
-   **MongoDB**: You need access to a MongoDB database. This can be a local installation or a cloud-based service like MongoDB Atlas (which offers a generous free tier).

## Step 2: Clone the Repository

Open your terminal, navigate to the directory where you want to store the project, and clone the repository.

```sh
git clone <your-repo-url>
cd ryuuko
```

## Step 3: Create and Activate a Virtual Environment

A virtual environment is crucial for isolating project dependencies. From the project root (`ryuuko`), run:

```sh
# Create the virtual environment in a folder named .venv
python3 -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .\.venv\Scripts\activate
```

Your terminal prompt should now be prefixed with `(.venv)`, indicating that the virtual environment is active.

## Step 4: Install Dependencies

The project uses a `pyproject.toml` file to manage dependencies. The most effective way to install everything is to use `pip`'s editable mode.

From the project root (`ryuuko`), run:

```sh
pip install -e ./packages/bot
```

This command tells `pip` to install the `ryuuko-bot` package in a way that allows you to edit the source code directly. It will also automatically find and install all dependencies listed in `pyproject.toml`, such as `discord.py`, `openai`, `pymongo`, and `Pillow`.

## Step 5: Configure Environment Variables

This is the most critical step for making the bot functional.

1.  Navigate to the bot's package directory:
    ```sh
    cd packages/bot
    ```

2.  Create your personal `.env` file from the example template:
    ```sh
    cp .env.example .env
    ```

3.  Open the `.env` file with a text editor and provide your credentials. **Do not share this file with anyone.**

    ```ini
    # Get this from the Discord Developer Portal
    DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN"

    # Get this from your MongoDB provider (e.g., MongoDB Atlas)
    MONGODB_CONNECTION_STRING="mongodb+srv://<user>:<password>@<cluster-url>/..."

    # Get this from Google AI Studio for Gemini models
    GEMINI_API_KEY="YOUR_GOOGLE_AI_STUDIO_API_KEY"

    # (Optional) Add other keys if you use these providers
    POLYDEVS_API_KEY=""
    PROXYVN_API_KEY=""
    ```

## Step 6: Review Configuration Files

The `packages/bot/config/` directory contains two important files:

-   `config.json`: Contains general bot settings, such as default models and provider settings. Review this file to understand how the bot is configured.
-   `instructions.json`: Contains the detailed system prompts used by the `polydevs` provider. You can customize these instructions to change the bot's personality and behavior for `ryuuko-r1-*` models.

## Step 7: Run the Bot

Once everything is installed and configured, navigate back to the project root (`ryuuko`) and run the bot as a Python module:

```sh
# Make sure you are in the root 'ryuuko' directory
python3 -m bot
```

If everything is set up correctly, you will see log messages in your terminal indicating that the bot has connected to Discord and is ready to receive commands.
