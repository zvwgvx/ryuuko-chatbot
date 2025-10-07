# Ryuuko — Monorepo

This repository contains the source code for the Ryuuko project, which includes a Discord Bot, a backend API, and a web dashboard.

## Overview

This project is structured as a monorepo, with each major component living in its own package.

*   `packages/bot`: The Discord bot, powered by Large Language Models.
*   `packages/api`: The backend API (FastAPI) that handles user authentication, data storage, and business logic.
*   `packages/web`: The frontend web dashboard for user interaction and configuration.

## Getting Started

These instructions will give you an overview of the project setup. For detailed instructions on a specific service, please refer to the `README.md` within that package's directory.

### Prerequisites

*   Python 3.10+
*   Node.js (for the web dashboard)
*   Docker and Docker Compose
*   MongoDB server

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/zvwgvx/ryuuko-chatbot.git
    cd ryuuko-chatbot
    ```

2.  **Configure environment variables:**
    *   Copy the `.env.example` file to a new `.env` file in the root directory.
        ```bash
        cp .env.example .env
        ```
    *   Fill in the required values in the `.env` file, such as your Discord token, database connection string, and JWT secret.

3.  **Service-specific setup:**
    *   For the **Discord Bot**, navigate to `packages/bot` and follow the instructions in its `README.md`.
    *   For the **API**, navigate to `packages/api` and follow the instructions in its `README.md`.
    *   For the **Web Dashboard**, navigate to `packages/web` and follow the instructions in its `README.md`.

## Documentation

For more detailed information about the project's architecture, contribution guidelines, and more, please refer to the `/docs` directory.

*   [**Architecture**](docs/ARCHITECTURE.md): An overview of the project's technical design.
*   [**Contributing**](CONTRIBUTING.md): Guidelines for contributing to the project.
*   [**License**](LICENSE): The project's license.
*   [**Security**](SECURITY.md): Information about the project's security policies.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.