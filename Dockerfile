# =================================================================
# STAGE 1: Build Stage
# =================================================================
# This stage installs dependencies for a specific package into a virtual environment.
# It leverages Docker caching, so dependencies are only re-installed if the
# package's pyproject.toml changes.
FROM python:3.11-slim-bookworm AS builder

# ARG to specify which package to build.
# This can be set during the build process, e.g., --build-arg PACKAGE_NAME=bot
ARG PACKAGE_NAME

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR=off

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies for the target package
WORKDIR /app
COPY packages/${PACKAGE_NAME}/pyproject.toml .
# Copy the src directory of the package to resolve local package structure
COPY packages/${PACKAGE_NAME}/src ./src
RUN pip install --upgrade pip
RUN pip install .

# =================================================================
# STAGE 2: Final Stage
# =================================================================
# This stage creates the final, lean image for running the application.
FROM python:3.11-slim-bookworm

# ARG to specify which package to run (must be the same as in the builder stage)
ARG PACKAGE_NAME

WORKDIR /app

# Copy the virtual environment with all dependencies from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application source code for the specific package
COPY packages/${PACKAGE_NAME}/src ./src
# Copy the package-specific config directory
COPY packages/${PACKAGE_NAME}/config ./config

# Activate the virtual environment and set the entrypoint
ENV PATH="/opt/venv/bin:$PATH"

# The CMD will execute the 'start' script defined in the package's pyproject.toml
CMD ["start"]