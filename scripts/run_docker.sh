#!/bin/bash

# This script automates the process of building and running the Ryuuko-Chatbot Docker container.

# --- Configuration ---
IMAGE_NAME="ryuuko-chatbot"
CONTAINER_NAME="ryuuko-bot-instance"
ENV_FILE=".env"

# --- Script Logic ---

# 1. Navigate to the project's root directory.
# This ensures the script can be run from anywhere.
cd "$(dirname "$0")/.." || exit 1

# 2. Pre-flight check: Ensure .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "---"
    echo "❌ ERROR: Environment file '$ENV_FILE' not found in the project root."
    echo "Please create it and add your MONGODB_CONNECTION_STRING and DISCORD_TOKEN."
    exit 1
fi
echo "Found '$ENV_FILE' file."

# 3. Stop and remove the existing container if it exists.
# The '|| true' part ensures that the script doesn't exit if the container doesn't exist.
echo "---"
echo "Stopping and removing existing container: $CONTAINER_NAME..."
docker stop $CONTAINER_NAME || true
docker rm $CONTAINER_NAME || true
echo "Container stopped and removed."

# 4. Build the Docker image.
# The -t flag tags the image with a memorable name.
echo "---"
echo "Building Docker image: $IMAGE_NAME..."
docker build -t $IMAGE_NAME .

# Check if the build was successful.
if [ $? -ne 0 ]; then
    echo "---"
    echo "Docker build failed. Please check the output above for errors."
    exit 1
fi

echo "Image built successfully."

# 5. Run the new container.
# -d: Run in detached mode (in the background).
# --name: Assign a name to the container.
# --env-file: Load environment variables from the .env file.
echo "---"
echo "Running new container: $CONTAINER_NAME..."
docker run -d --name $CONTAINER_NAME --env-file .env $IMAGE_NAME

# Check if the 'docker run' command itself failed.
if [ $? -ne 0 ]; then
    echo "---"
    echo "Failed to start Docker container. Please check your Docker setup and the .env file."
    exit 1
fi

echo "Container '$CONTAINER_NAME' has been started."

# 6. Show the container logs.
echo "---"
echo "Showing logs for container '$CONTAINER_NAME'. Press Ctrl+C to stop viewing logs."
docker logs -f $CONTAINER_NAME
