# Deployment Guide

This document provides instructions and best practices for deploying the Ryuuko Bot to a production environment.

## 1. Server Preparation

It is highly recommended to run the bot on a dedicated server or VPS (Virtual Private Server) for 24/7 uptime. A lightweight Linux distribution (such as Ubuntu 22.04) is a suitable choice.

Ensure your server has Python 3.11+ and `git` installed.

## 2. Using a Service Manager

To ensure the bot runs continuously and restarts automatically after a server reboot or a crash, you should run it as a system service. `systemd` is the standard service manager on most modern Linux systems.

### Example `systemd` Service File

1.  Create a service file:
    ```sh
    sudo nano /etc/systemd/system/ryuuko.service
    ```

2.  Paste the following configuration into the file. **Remember to replace `/path/to/ryuuko` and `your_user` with your actual project path and username.**

    ```ini
    [Unit]
    Description=Ryuuko Discord Bot
    After=network.target

    [Service]
    # User and Group that will run the bot
    User=your_user
    Group=your_user

    # The root directory of the project
    WorkingDirectory=/path/to/ryuuko

    # The command to start the bot
    # This assumes your virtual environment is named .venv inside the project root
    ExecStart=/path/to/ryuuko/.venv/bin/python3 -m bot

    # Restart policy
    Restart=always
    RestartSec=10

    # Standard output and error logging
    StandardOutput=journal
    StandardError=journal
    SyslogIdentifier=ryuuko

    [Install]
    WantedBy=multi-user.target
    ```

3.  **Enable and Start the Service:**
    ```sh
    # Reload systemd to recognize the new service
    sudo systemctl daemon-reload

    # Enable the service to start on boot
    sudo systemctl enable ryuuko.service

    # Start the service immediately
    sudo systemctl start ryuuko.service
    ```

4.  **Check the Service Status:**
    You can check if the bot is running correctly and view its logs using:
    ```sh
    sudo systemctl status ryuuko.service
    journalctl -u ryuuko -f
    ```

## 3. Security Best Practices

-   **Principle of Least Privilege**: Do not run the bot as the `root` user. Create a dedicated user account with limited permissions for running the bot process.

-   **Secure the `.env` File**: On your production server, ensure the `.env` file has restrictive permissions so that only the bot's user can read it.
    ```sh
    chmod 600 /path/to/ryuuko/packages/bot/.env
    ```

-   **Firewall**: Configure a firewall (like `ufw` on Ubuntu) to only allow necessary incoming and outgoing traffic. The bot primarily makes outbound HTTPS requests, so strict inbound rules can be applied.

-   **Regular Updates**: Keep the server's operating system and all bot dependencies updated to patch potential security vulnerabilities.
    ```sh
    # From your project root
    source .venv/bin/activate
    pip install --upgrade -e ./packages/bot
    sudo systemctl restart ryuuko
    ```

## 4. Environment Variables

Unlike in development, you should not commit your `.env` file. Instead, you should create it directly on the production server. Ensure all required variables from `.env.example` are present and correctly configured in your production `.env` file.
