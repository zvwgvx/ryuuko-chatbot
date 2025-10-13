# Deployment Guide v2.0.0

This document provides instructions for deploying the Ryuuko Bot v2.0.0 ecosystem to a production environment. This architecture requires running two separate, persistent services: the **Core Service** and the **Discord Bot**.

## 1. Server Preparation

-   **Environment**: A Linux VPS (e.g., Ubuntu 22.04) is recommended for 24/7 uptime.
-   **Prerequisites**: Ensure your server has Python 3.11+, `git`, and a firewall (like `ufw`) configured.
-   **Installation**: Follow the installation steps in `SETUP.md` to clone the repository, create a virtual environment, and install all dependencies for both `core` and `discord-bot`.

## 2. Using `systemd` for Service Management

To ensure both services run continuously and restart automatically, we will create a `systemd` service file for each.

### A. Core Service (`ryuuko-core.service`)

This service runs the FastAPI backend API.

1.  **Create the service file:**
    ```sh
    sudo nano /etc/systemd/system/ryuuko-core.service
    ```

2.  **Paste the following configuration.** Replace `/path/to/ryuuko` and `your_user` with your actual project path and username.

    ```ini
    [Unit]
    Description=Ryuuko Core API Service
    After=network.target

    [Service]
    User=your_user
    Group=your_user
    WorkingDirectory=/path/to/ryuuko
    # Command to run the Core Service module
    ExecStart=/path/to/ryuuko/.venv/bin/python3 -m core
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target
    ```

### B. Discord Bot Service (`ryuuko-discord.service`)

This service runs the Discord client, which connects to the Core Service.

1.  **Create the service file:**
    ```sh
    sudo nano /etc/systemd/system/ryuuko-discord.service
    ```

2.  **Paste the following configuration.** Again, replace the placeholder paths and username.

    ```ini
    [Unit]
    Description=Ryuuko Discord Bot Client
    # Ensure the Core Service is started first
    After=network.target ryuuko-core.service
    Requires=ryuuko-core.service

    [Service]
    User=your_user
    Group=your_user
    WorkingDirectory=/path/to/ryuuko
    # Command to run the Discord Bot module
    ExecStart=/path/to/ryuuko/.venv/bin/python3 -m discord_bot
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target
    ```

### C. Managing the Services

After creating both files, run the following commands:

```sh
# Reload systemd to recognize the new services
sudo systemctl daemon-reload

# Enable both services to start on boot
sudo systemctl enable ryuuko-core.service
sudo systemctl enable ryuuko-discord.service

# Start both services immediately
sudo systemctl start ryuuko-core.service
sudo systemctl start ryuuko-discord.service
```

To check the status or view logs for a service, use:

```sh
sudo systemctl status ryuuko-core
journalctl -u ryuuko-core -f

sudo systemctl status ryuuko-discord
journalctl -u ryuuko-discord -f
```

## 3. Security Best Practices

-   **Firewall**: Configure your firewall to only allow traffic on necessary ports. The Core Service runs on port 8000, but you should ideally place it behind a reverse proxy like Nginx or Caddy and only expose ports 80/443.
-   **Restrictive Permissions**: Ensure your `.env` files are not world-readable. Set permissions to `600`.
    ```sh
    chmod 600 /path/to/ryuuko/packages/core/.env
    chmod 600 /path/to/ryuuko/packages/discord-bot/.env
    ```
-   **Dedicated User**: Run the services under a dedicated, non-root user account.
