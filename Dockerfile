# =================================================================
# STAGE 1: Build Stage
# =================================================================
# This stage installs dependencies into a virtual environment.
# It leverages Docker caching, so dependencies are only re-installed
# if pyproject.toml changes.
FROM python:3.11-slim-bookworm AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR=off

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
WORKDIR /app
COPY pyproject.toml .
RUN pip install --upgrade pip
# We copy the packages directory here because `pip install .` needs it to resolve the project structure
COPY packages ./packages
RUN pip install .

# =================================================================
# STAGE 2: Final Stage
# =================================================================
# This stage creates the final, lean image for running the application.
FROM python:3.11-slim-bookworm

WORKDIR /app

# Copy the virtual environment with all dependencies from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application source code
COPY . .

# Activate the virtual environment and run the application
ENV PATH="/opt/venv/bin:$PATH"
CMD ["start"]