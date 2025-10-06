#!/bin/bash

# This script automates the process of building and running the Ryuuko-Chatbot Docker container.

# Set the name for the Docker image and container for consistency.
IMAGE_NAME="ryuuko-chatbot"
CONTAINER_NAME="ryuuko-bot-instance"

# Navigate to the project's root directory.
# This ensures the script can be run from anywhere.
cd "$(dirname "$0")/.."

# Stop and remove the existing container if it exists.
# The '|| true' part ensures that the script doesn't exit if the container doesn't exist.
echo "---" 
echo "Stopping and removing existing container: $CONTAINER_NAME..."
docker stop $CONTAINER_NAME || true
docker rm $CONTAINER_NAME || true
echo "Container stopped and removed."

# Build the Docker image.
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

# Run the new container.
# -d: Run in detached mode (in the background).
# --name: Assign a name to the container.
# --env-file: Load environment variables from the .env file.
echo "---"
echo "Running new container: $CONTAINER_NAME..."
docker run -d --name $CONTAINER_NAME --env-file .env $IMAGE_NAME

# Check if the container started successfully.
if [ $? -ne 0 ]; then
    echo "---"
    echo "Failed to start Docker container. Please check your Docker setup and the .env file."
    exit 1
fi

echo "Container started successfully."
