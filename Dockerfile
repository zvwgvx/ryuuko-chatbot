# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables to ensure logs are sent straight to stdout
# and that Python doesn't generate .pyc files.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy the requirements file first to leverage Docker's layer caching.
# The pip install step will only be re-run if requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container.
# The .dockerignore file will prevent unnecessary files from being copied.
COPY . .

# Command to run the application as a module
CMD ["python3", "-m", "src"]
