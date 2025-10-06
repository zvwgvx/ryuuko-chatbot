# Contributing to Ryuuko Discord Bot

First off, thank you for considering contributing to Ryuuko! It's people like you that make this project great.

## Code of Conduct

This project and everyone participating in it is governed by the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## How Can I Contribute?

### Reporting Bugs

If you find a bug, please open an issue on our [GitHub repository](httpss://github.com/your-github-username/your-repository-name/issues). Please include a clear title, a description of the issue, and steps to reproduce it.

### Suggesting Enhancements

If you have an idea for a new feature or an improvement to an existing one, please open an issue to discuss it. This allows us to coordinate our efforts and prevent duplication of work.

### Your First Code Contribution

Unsure where to begin contributing? You can start by looking through `good first issue` and `help wanted` issues.

## Development Setup

1.  **Fork the repository** on GitHub.
2.  **Clone your fork** locally:
    ```bash
    git clone https://github.com/your-github-username/your-repository-name.git
    cd your-repository-name
    ```
3.  **Create a new branch** for your changes:
    ```bash
    git checkout -b your-feature-branch
    ```
4.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
5.  **Set up your environment**:
    -   Create a `.env` file in the project root.
    -   Add your `DISCORD_TOKEN` and `MONGODB_CONNECTION_STRING`.
    ```env
    DISCORD_TOKEN=your_discord_bot_token
    MONGODB_CONNECTION_STRING=your_mongodb_connection_string
    ```

## Coding Style

-   Please follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for Python code.
-   Use clear and descriptive names for variables, functions, and classes.
-   Add comments to your code where necessary to explain complex logic.
-   Write docstrings for all modules, classes, and functions.

## Testing

Before submitting your changes, please ensure that all existing tests pass and that you have added new tests for any new functionality.

To run the test suite:
```bash
python -m pytest
```

## Submitting Changes

1.  **Commit your changes** with a clear and descriptive commit message.
2.  **Push your branch** to your fork on GitHub:
    ```bash
    git push origin your-feature-branch
    ```
3.  **Open a pull request** to the `main` branch of the original repository.
4.  In the pull request description, please explain the changes you have made and link to any relevant issues.

We will review your pull request as soon as possible. Thank you for your contribution!