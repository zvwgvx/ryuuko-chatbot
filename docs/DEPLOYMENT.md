# Deployment Guide v3.0.0

This document provides instructions for deploying the Ryuuko Chatbot ecosystem to a production environment. The system consists of multiple independent services that can be deployed separately: **Core API Service**, **Discord Bot**, **Telegram Bot**, and **Web Dashboard**.

## Prerequisites

- **Linux VPS** (Ubuntu 22.04 LTS recommended) or similar server
- **Python 3.11+** installed
- **Git** installed
- **MongoDB** instance (Atlas or self-hosted)
- **Node.js 18+** (only for Web Dashboard)
- **Nginx** or **Caddy** (recommended for reverse proxy)
- **Domain name** (optional but recommended for HTTPS)

## Deployment Options

This guide covers two deployment methods:
1. **systemd Services** (recommended for VPS/dedicated servers)
2. **Docker** (recommended for containerized deployments)

---

## Method 1: systemd Service Deployment

This method runs services as persistent systemd services with automatic restart on failure.

### Step 1: Server Preparation

#### Update System
```bash
sudo apt update && sudo apt upgrade -y
```

#### Install Python 3.11+ (if not available)
```bash
sudo apt install python3.11 python3.11-venv python3-pip -y
```

#### Install Node.js (for Web Dashboard)
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

#### Configure Firewall
```bash
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable
```

### Step 2: Clone and Install

#### Create Deployment User (recommended for security)
```bash
sudo useradd -m -s /bin/bash ryuuko
sudo su - ryuuko
```

#### Clone Repository
```bash
cd ~
git clone https://github.com/zvwgvx/ryuuko-chatbot
cd ryuuko-chatbot
```

#### Create Virtual Environment
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

#### Install Python Packages
```bash
# Core API (required)
pip install -e ./packages/ryuuko-api

# Discord bot (optional)
pip install -e ./packages/discord-bot

# Telegram bot (optional)
pip install -e ./packages/telegram-bot
```

#### Install Dashboard Dependencies (optional)
```bash
cd packages/dashboard
npm install
npm run build  # Creates optimized production build
cd ../..
```

### Step 3: Environment Configuration

Create `.env` files for each service. **Important**: Use production-grade values!

#### Core API (.env)
```bash
nano packages/ryuuko-api/.env
```

```env
# MongoDB Connection (use MongoDB Atlas or self-hosted)
MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/ryuuko

# API Security - GENERATE STRONG KEYS!
CORE_API_KEY=your-secure-random-key-minimum-32-characters-long

# LLM Provider API Keys
GEMINI_API_KEY=your-production-gemini-key
POLYDEVS_API_KEY=your-production-polydevs-key
PROXYVN_API_KEY=your-production-proxyvn-key

# JWT Secret - GENERATE STRONG KEY!
SECRET_KEY=your-jwt-secret-minimum-32-characters-long

# Server Configuration
HOST=127.0.0.1  # Localhost only (behind reverse proxy)
PORT=8000
```

#### Discord Bot (.env)
```bash
nano packages/discord-bot/.env
```

```env
DISCORD_TOKEN=your-production-discord-token
CORE_API_URL=http://127.0.0.1:8000
CORE_API_KEY=<same-as-core-api>
```

#### Telegram Bot (.env)
```bash
nano packages/telegram-bot/.env
```

```env
TELEGRAM_TOKEN=your-production-telegram-token
CORE_API_URL=http://127.0.0.1:8000
CORE_API_KEY=<same-as-core-api>
```

#### Secure .env Files
```bash
chmod 600 packages/ryuuko-api/.env
chmod 600 packages/discord-bot/.env
chmod 600 packages/telegram-bot/.env
```

### Step 4: Create systemd Services

Exit from ryuuko user back to your sudo user:
```bash
exit
```

#### A. Core API Service

Create service file:
```bash
sudo nano /etc/systemd/system/ryuuko-api.service
```

```ini
[Unit]
Description=Ryuuko Core API Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=ryuuko
Group=ryuuko
WorkingDirectory=/home/ryuuko/ryuuko-chatbot
Environment="PATH=/home/ryuuko/ryuuko-chatbot/.venv/bin"
ExecStart=/home/ryuuko/ryuuko-chatbot/.venv/bin/python3 -m ryuuko_api
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### B. Discord Bot Service

```bash
sudo nano /etc/systemd/system/ryuuko-discord.service
```

```ini
[Unit]
Description=Ryuuko Discord Bot Client
After=network.target ryuuko-api.service
Wants=network-online.target
Requires=ryuuko-api.service

[Service]
Type=simple
User=ryuuko
Group=ryuuko
WorkingDirectory=/home/ryuuko/ryuuko-chatbot
Environment="PATH=/home/ryuuko/ryuuko-chatbot/.venv/bin"
ExecStart=/home/ryuuko/ryuuko-chatbot/.venv/bin/python3 -m discord_bot
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### C. Telegram Bot Service

```bash
sudo nano /etc/systemd/system/ryuuko-telegram.service
```

```ini
[Unit]
Description=Ryuuko Telegram Bot Client
After=network.target ryuuko-api.service
Wants=network-online.target
Requires=ryuuko-api.service

[Service]
Type=simple
User=ryuuko
Group=ryuuko
WorkingDirectory=/home/ryuuko/ryuuko-chatbot
Environment="PATH=/home/ryuuko/ryuuko-chatbot/.venv/bin"
ExecStart=/home/ryuuko/ryuuko-chatbot/.venv/bin/python3 -m telegram_bot
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Step 5: Enable and Start Services

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable ryuuko-api.service
sudo systemctl enable ryuuko-discord.service   # Optional
sudo systemctl enable ryuuko-telegram.service  # Optional

# Start services
sudo systemctl start ryuuko-api.service
sudo systemctl start ryuuko-discord.service    # Optional
sudo systemctl start ryuuko-telegram.service   # Optional
```

### Step 6: Verify Services

```bash
# Check status
sudo systemctl status ryuuko-api
sudo systemctl status ryuuko-discord
sudo systemctl status ryuuko-telegram

# View logs
sudo journalctl -u ryuuko-api -f
sudo journalctl -u ryuuko-discord -f
sudo journalctl -u ryuuko-telegram -f
```

---

## Method 2: Docker Deployment

Docker provides containerized deployment for easier management and portability.

### Step 1: Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose -y

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Step 2: Build Docker Images

#### Build Core API
```bash
docker build --build-arg PACKAGE_NAME=ryuuko-api -t ryuuko-api:latest .
```

#### Build Discord Bot
```bash
docker build --build-arg PACKAGE_NAME=discord-bot -t ryuuko-discord-bot:latest .
```

#### Build Telegram Bot
```bash
docker build --build-arg PACKAGE_NAME=telegram-bot -t ryuuko-telegram-bot:latest .
```

### Step 3: Create Docker Compose File

```bash
nano docker-compose.yml
```

```yaml
version: '3.8'

services:
  api:
    image: ryuuko-api:latest
    container_name: ryuuko-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - ./packages/ryuuko-api/.env
    networks:
      - ryuuko-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3

  discord-bot:
    image: ryuuko-discord-bot:latest
    container_name: ryuuko-discord
    restart: unless-stopped
    env_file:
      - ./packages/discord-bot/.env
    depends_on:
      - api
    networks:
      - ryuuko-network

  telegram-bot:
    image: ryuuko-telegram-bot:latest
    container_name: ryuuko-telegram
    restart: unless-stopped
    env_file:
      - ./packages/telegram-bot/.env
    depends_on:
      - api
    networks:
      - ryuuko-network

networks:
  ryuuko-network:
    driver: bridge
```

### Step 4: Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## Security & Monitoring

### SSL Setup with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d api.yourdomain.com
```

### Regular Updates

```bash
# systemd
sudo su - ryuuko
cd ~/ryuuko-chatbot
git pull origin main
source .venv/bin/activate
pip install -e ./packages/ryuuko-api --upgrade
exit
sudo systemctl restart ryuuko-api

# Docker
git pull origin main
docker-compose build
docker-compose down && docker-compose up -d
```

---

**Your Ryuuko Chatbot ecosystem is now deployed!** 🚀
