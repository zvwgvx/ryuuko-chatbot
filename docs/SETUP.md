# Detailed Setup Guide v2.0.0

This guide provides a step-by-step walkthrough for setting up the entire Ryuuko Bot v2.0.0 ecosystem for development.

## Step 1: System Prerequisites

-   **Python**: Version 3.11 or higher.
-   **Git**: For cloning the repository.
-   **MongoDB**: A running MongoDB instance (local or cloud-hosted, e.g., MongoDB Atlas).

## Step 2: Clone the Repository

Open your terminal and clone the project repository.

```sh
git clone <your-repo-url>
cd ryuuko
```

## Step 3: Create and Activate a Virtual Environment

From the project root (`ryuuko/`), create a single virtual environment for the entire project.

```sh
# Create the virtual environment
python3 -m venv .venv

# Activate it (on macOS/Linux)
source .venv/bin/activate
```

## Step 4: Install All Dependencies

The project is now split into two main packages: `core` and `discord-bot`. You need to install both.

From the project root (`ryuuko/`), run the following commands:

```sh
# Install the Core Service dependencies
pip install -e ./packages/core

# Install the Discord Bot client dependencies
pip install -e ./packages/discord-bot
```

This installs both packages in "editable" mode, so changes you make to the code are immediately reflected.

## Step 5: Configure Environment Variables

This is the most critical step. You must configure two separate `.env` files.

### A. Configure the Core Service

1.  Navigate to the Core Service package:
    ```sh
    cd packages/core
    ```
2.  Create the `.env` file from the example:
    ```sh
    cp .env.example .env
    ```
3.  Edit `.env` and fill in your credentials:
    -   `CORE_API_KEY`: Create a strong, secret key. This will be used to protect your API.
    -   `MONGODB_CONNECTION_STRING`: Your full MongoDB connection URI.
    -   `GEMINI_API_KEY`, `POLYDEVS_API_KEY`, etc.: Fill in the keys for the LLM providers you intend to use.

### B. Configure the Discord Bot

1.  Navigate to the Discord Bot package:
    ```sh
    cd ../discord-bot  # Assuming you are in packages/core
    ```
2.  Create the `.env` file:
    ```sh
    cp .env.example .env
    ```
3.  Edit `.env` and fill in the values:
    -   `DISCORD_TOKEN`: Your Discord bot token.
    -   `CORE_API_URL`: The URL where your Core Service will run. For local development, the default `http://127.0.0.1:8000` is usually correct.
    -   `CORE_API_KEY`: The **exact same** secret key you created for the Core Service.

## Step 6: Run the Ecosystem

To run the bot, you need to start both services in two separate terminals from the project root (`ryuuko/`).

**➡️ In Terminal 1, start the Core Service:**

```sh
# Make sure you are in the project root (ryuuko/)
python3 -m core
```

**⬅️ In Terminal 2, start the Discord Bot:**

```sh
# Make sure you are in the project root (ryuuko/)
python3 -m discord_bot
```

Once both services are running, your bot will be online and ready to use.
