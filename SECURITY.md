# Security Policy

This document outlines the security procedures and policies for the Ryuuko Bot project.

## Supported Versions

Security updates are only applied to the latest version of the code available on the `main` branch. We encourage all users to run the most current version of the bot to ensure they have the latest security patches.

| Version | Supported          |
| ------- | ------------------ |
| > 1.3.x | :white_check_mark: |

## Reporting a Vulnerability

The Ryuuko Bot team and community take all security vulnerabilities seriously. We appreciate your efforts to responsibly disclose your findings, and will make every effort to acknowledge your contributions.

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them directly to us via email at:

**[security@example.com](mailto:security@example.com)** (Please replace with a real email address)

Please include the following details in your report:

- A clear description of the vulnerability and its potential impact.
- Steps to reproduce the vulnerability, including any specific commands, inputs, or configurations.
- The version of the bot you are running, if known.
- Any potential mitigations you have considered.

We will make our best effort to respond to your report within 48 hours and provide a timeline for a fix.

## Security Measures in Place

This project has been developed with several security considerations in mind:

### 1. Credential Management

- **Environment Variables**: All sensitive information, including the Discord bot token, MongoDB connection string, and all third-party API keys, are managed exclusively through an `.env` file.
- **`.gitignore`**: The `.env` file is explicitly included in the project's `.gitignore` to prevent accidental commits of sensitive credentials to version control.

### 2. Access Control

- **Owner-Only Commands**: Critical administrative commands (e.g., user management, credit management, model configuration) are strictly restricted to the bot owner, as defined in the Discord application.
- **Authorization System**: The bot includes a whitelist-based authorization system (`authorized_users`). Only users on this list can interact with the bot's core AI features, preventing unauthorized use.

### 3. Input Handling

- **Mention Stripping**: The bot automatically strips its own mention (`@Ryuuko`) from user prompts to prevent it from being processed as part of the input to the language model.
- **Attachment Processing**: File attachments are validated by size and MIME type/extension before being processed to prevent abuse and handling of excessively large or unsupported files.

### 4. Dependency Management

- **Defined Dependencies**: All project dependencies are clearly defined in `pyproject.toml`. This ensures a consistent and predictable environment and makes it easier to audit for vulnerable packages.

## Security Best Practices for Deployment

- **Secure your `.env` file**: Ensure that the `.env` file on your production server has restrictive file permissions (e.g., `600`) so that only the user running the bot can read it.
- **Principle of Least Privilege**: Run the bot process under a dedicated, non-root user account with the minimum permissions necessary for its operation.
- **Keep Dependencies Updated**: Regularly update your local dependencies to ensure you have the latest security patches from upstream libraries:
  ```sh
  pip install --upgrade -e ./packages/bot
  ```
