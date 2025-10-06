# Deployment Guide

This guide provides instructions on how to deploy the Ryuuko Discord Bot using Docker. Containerization with Docker is the recommended method for running the bot in a production environment because it ensures consistency and simplifies dependency management.

## Prerequisites

-   **Docker**: You must have Docker installed and running on your deployment server. You can find installation instructions for your operating system on the [official Docker website](https://docs.docker.com/get-docker/).

## Deployment Steps

### 1. Build the Docker Image

From the root directory of the project, run the following command to build the Docker image. The `Dockerfile` included in the repository contains all the necessary instructions to create a production-ready image.

```bash
docker build -t ryuuko-bot .
```

This command will:
-   Use the official Python 3.11 slim image as a base.
-   Install all the required Python dependencies from `requirements.txt`.
-   Copy the application code into the image.

### 2. Prepare the Environment File

Before running the container, you need to provide the necessary environment variables. Create a file named `prod.env` (or any other name you prefer) in a secure location on your server. This file will contain the bot's secrets.

```env
# prod.env

# Your Discord bot token
DISCORD_TOKEN="your_production_discord_bot_token"

# Your production MongoDB connection string
MONGODB_CONNECTION_STRING="mongodb://user:password@production-db-host:port/"
```

**Note**: Do not commit this file to your version control system.

### 3. Run the Docker Container

Once the image is built and your environment file is ready, you can start the bot using the `docker run` command.

```bash
docker run -d \
  --name ryuuko-bot-container \
  --env-file ./prod.env \
  -v ./config.json:/app/config.json \
  -v ./logs:/app/logs \
  --restart unless-stopped \
  ryuuko-bot
```

Let's break down this command:
-   `-d`: Runs the container in detached mode (in the background).
-   `--name ryuuko-bot-container`: Assigns a name to the container for easy management.
-   `--env-file ./prod.env`: Passes the environment variables from your `prod.env` file to the container.
-   `-v ./config.json:/app/config.json`: Mounts your local `config.json` file into the container. This allows you to change the configuration without rebuilding the image.
-   `-v ./logs:/app/logs`: Mounts a local `logs` directory into the container to persist log files.
-   `--restart unless-stopped`: Configures the container to automatically restart if it crashes, unless it has been manually stopped.
-   `ryuuko-bot`: The name of the image to run.

## Managing the Container

Here are some useful Docker commands for managing your running bot:

-   **View logs**:
    ```bash
    docker logs -f ryuuko-bot-container
    ```

-   **Stop the container**:
    ```bash
    docker stop ryuuko-bot-container
    ```

-   **Start the container**:
    ```bash
    docker start ryuuko-bot-container
    ```

-   **Remove the container**:
    ```bash
    docker rm ryuuko-bot-container
    ```

By following these steps, you can deploy a stable and maintainable instance of the Ryuuko Discord Bot.