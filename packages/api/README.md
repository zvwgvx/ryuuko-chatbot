# Ryuuko API

This package contains the backend API for the Ryuuko project. It is built with FastAPI and handles user authentication, data management, and other core business logic.

## Getting Started

### Prerequisites

*   Python 3.10+
*   A running MongoDB instance
*   Environment variables configured (see below)

### Installation

1.  **Navigate to the API package directory:**
    ```bash
    cd packages/api
    ```

2.  **Install dependencies:**
    It is recommended to use a virtual environment.
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    pip install -e .[test]
    ```

### Configuration

This service requires the following environment variables to be set. You can add them to a `.env` file in the root of the monorepo.

*   `MONGODB_CONNECTION_STRING`: The connection string for your MongoDB database.
*   `JWT_SECRET_KEY`: A strong, secret key for signing JWTs.
*   `JWT_ALGORITHM`: The algorithm to use for JWTs (e.g., `HS256`).

### Usage

To run the API server locally, use the following command from the `packages/api` directory:

```bash
uvicorn src.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. You can access the auto-generated documentation at `http://127.0.0.1:8000/docs`.