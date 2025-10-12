# Bot Commands Reference

This document provides a detailed list of all commands available in the Ryuuko Bot.

## 👤 User Commands

These commands are available to all authorized users.

### `.help`

-   **Description**: Displays a list of available commands based on your permission level.
-   **Usage**: `.help`

### `.ping`

-   **Description**: Checks the bot's API and WebSocket latency.
-   **Usage**: `.ping`

### `.model <model_name>`

-   **Description**: Sets your preferred AI model for all future conversations.
-   **Usage**: `.model <model_name>`
-   **Example**: `.model ryuuko-r1-vnm-pro`

### `.models`

-   **Description**: Lists all available AI models, grouped by access level and showing their credit cost.
-   **Usage**: `.models`

### `.profile [user]`

-   **Description**: Displays your configuration profile, including your current model, credit balance, and access level. Bot owners can view the profile of other users.
-   **Usage**: `.profile` or `.profile @mention`
-   **Example**: `.profile @ZangVu`

### `.clearmemory`

-   **Description**: Clears your personal conversation history. This is useful to start a new topic without the bot being influenced by past context.
-   **Usage**: `.clearmemory`

---

## 👑 Admin & Owner Commands

These commands are restricted to the bot owner for security and administrative purposes.

### `.memory [user]`

-   **Description**: Inspects the last 10 messages in the conversation history for a user. If no user is specified, it shows your own memory.
-   **Usage**: `.memory` or `.memory @mention`
-   **Example**: `.memory @ZangVu`

### `.auth <user>`

-   **Description**: Authorizes a new user, allowing them to interact with the bot.
-   **Usage**: `.auth @mention`

### `.deauth <user>`

-   **Description**: Revokes a user's authorization.
-   **Usage**: `.deauth @mention`

### `.auths`

-   **Description**: Lists all currently authorized user IDs. If the list is long, it will be sent as a text file.
-   **Usage**: `.auths`

### `.addmodel <name> <cost> <level>`

-   **Description**: Adds a new supported AI model to the database.
-   **Usage**: `.addmodel <model_name> <credit_cost> <access_level>`
-   **Example**: `.addmodel gpt-4o-mini 150 1`

### `.removemodel <name>`

-   **Description**: Removes a model from the database. This will fail if any user is currently using the model.
-   **Usage**: `.removemodel <model_name>`
-   **Example**: `.removemodel gpt-3.5-turbo`

### `.editmodel <name> <cost> <level>`

-   **Description**: Edits the credit cost and access level of an existing model.
-   **Usage**: `.editmodel <model_name> <new_credit_cost> <new_access_level>`
-   **Example**: `.editmodel gpt-4o-mini 200 2`

### `.addcredit <user> <amount>`

-   **Description**: Adds a specified amount of credits to a user's balance.
-   **Usage**: `.addcredit @mention <amount>`
-   **Example**: `.addcredit @ZangVu 10000`

### `.setcredit <user> <amount>`

-   **Description**: Sets a user's credit balance to a specific, absolute amount.
-   **Usage**: `.setcredit @mention <amount>`
-   **Example**: `.setcredit @ZangVu 5000`

### `.setlevel <user> <level>`

-   **Description**: Sets a user's access level (0: Basic, 1: Advanced, 2: Ultimate).
-   **Usage**: `.setlevel @mention <level>`
-   **Example**: `.setlevel @ZangVu 2`
