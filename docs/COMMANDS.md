# Command Reference

This document provides a comprehensive reference for all commands available in the Ryuuko Discord Bot. Commands are grouped by their required permission levels.

The default command prefix is `.`

---

## 👤 User Commands

These commands are available to all authorized users.

### General

-   `.ping`
    -   **Description**: Checks the bot's latency, including API response time and WebSocket latency.
    -   **Usage**: `.ping`

-   `.help`
    -   **Description**: Displays a help message with a list of available commands based on your permission level.
    -   **Usage**: `.help`

### Configuration

-   `.model <model_name>`
    -   **Description**: Sets your preferred AI model for conversations.
    -   **Usage**: `.model gpt-4`

-   `.sysprompt <prompt>`
    -   **Description**: Sets a custom system prompt to tailor the AI's personality or behavior.
    -   **Usage**: `.sysprompt You are a helpful assistant.`

-   `.profile [user]`
    -   **Description**: Shows your configuration profile, including your current model, credit balance, and access level. Bot owners can view other users' profiles.
    -   **Usage**: `.profile` or `.profile @username`

-   `.showprompt [user]`
    -   **Description**: Displays your current system prompt. Bot owners can view other users' prompts.
    -   **Usage**: `.showprompt` or `.showprompt @username`

-   `.models`
    -   **Description**: Lists all available AI models, categorized by access level and showing credit costs.
    -   **Usage**: `.models`

-   `.clearmemory`
    -   **Description**: Clears your entire conversation history with the bot.
    -   **Usage**: `.clearmemory`

---

## 👑 Owner Commands

These commands are restricted to the bot owner and are used for administration and system management.

### User Management

-   `.auth <user>`
    -   **Description**: Authorizes a user to interact with the bot.
    -   **Usage**: `.auth @username`

-   `.deauth <user>`
    -   **Description**: Revokes a user's authorization.
    -   **Usage**: `.deauth @username`

-   `.auths`
    -   **Description**: Lists all currently authorized user IDs.
    -   **Usage**: `.auths`

-   `.memory [user]`
    -   **Description**: Inspects the recent conversation history for a specific user. If no user is provided, it shows the history of the command author.
    -   **Usage**: `.memory @username`

### Model Management

-   `.addmodel <name> <cost> <level>`
    -   **Description**: Adds a new AI model to the list of supported models.
    -   **Usage**: `.addmodel gpt-4-turbo 10 2`

-   `.removemodel <name>`
    -   **Description**: Removes an AI model from the system.
    -   **Usage**: `.removemodel gpt-3.5-turbo`

-   `.editmodel <name> <cost> <level>`
    -   **Description**: Edits the credit cost and access level of an existing model.
    -   **Usage**: `.editmodel gpt-4 15 2`

### Credit & Access Management

-   `.addcredit <user> <amount>`
    -   **Description**: Adds credits to a user's balance.
    -   **Usage**: `.addcredit @username 100`

-   `.deductcredit <user> <amount>`
    -   **Description**: Deducts credits from a user's balance.
    -   **Usage**: `.deductcredit @username 50`

-   `.setcredit <user> <amount>`
    -   **Description**: Sets a user's credit balance to a specific value.
    -   **Usage**: `.setcredit @username 500`

-   `.setlevel <user> <level>`
    -   **Description**: Sets a user's access level (0: Basic, 1: Advanced, 2: Ultimate).
    -   **Usage**: `.setlevel @username 1`