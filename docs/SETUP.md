# Detailed Setup Guide v3.0.0

This guide provides a comprehensive walkthrough for setting up the entire Ryuuko Chatbot ecosystem for development, including the Core API, Discord bot, Telegram bot, and Web Dashboard.

## System Prerequisites

Before starting, ensure you have the following installed:

- **Python 3.11+** (recommended: Python 3.13)
  ```bash
  python3 --version  # Should show 3.11 or higher
  ```

- **Git** for cloning the repository
  ```bash
  git --version
  ```

- **MongoDB** (local or cloud-hosted)
  - **Local**: Install MongoDB Community Edition
  - **Cloud**: Create a free cluster on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)

- **Node.js 18+** (only required for Web Dashboard)
  ```bash
  node --version  # Should show 18.x or higher
  npm --version
  ```

## Step 1: Clone the Repository

```bash
git clone https://github.com/zvwgvx/ryuuko-chatbot
cd ryuuko-chatbot
```

## Step 2: Create and Activate Virtual Environment

From the project root (`ryuuko-chatbot/`), create a single virtual environment for all Python packages:

```bash
# Create the virtual environment
python3 -m venv .venv

# Activate it
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

Your terminal prompt should now show `(.venv)` prefix.

## Step 3: Install Python Dependencies

Install the packages you plan to use. All packages should be installed in **editable mode** (`-e`) so changes to the code are immediately reflected.

### Core API (Required)

The Core API is required for all functionality:

```bash
pip install -e ./packages/ryuuko-api
```

This installs:
- FastAPI, Uvicorn
- MongoDB drivers (pymongo)
- LLM providers (google-generativeai, openai)
- Sentence transformers for semantic search
- Authentication (PyJWT, passlib, bcrypt)
- All other dependencies

### Discord Bot Client (Optional)

If you want to run the Discord bot:

```bash
pip install -e ./packages/discord-bot
```

This installs:
- discord.py
- httpx (for API communication)
- Pillow (for image processing)

### Telegram Bot Client (Optional)

If you want to run the Telegram bot:

```bash
pip install -e ./packages/telegram-bot
```

This installs:
- python-telegram-bot
- httpx
- Pillow

### Verify Installation

Check that packages are installed correctly:

```bash
pip list | grep ryuuko
# Should show: ryuuko-api, ryuuko-discord-bot, ryuuko-telegram-bot
```

## Step 4: MongoDB Setup

### Option A: MongoDB Atlas (Cloud - Recommended for beginners)

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free account
3. Create a new cluster (M0 Free tier is sufficient for development)
4. Wait for cluster to be created (~5 minutes)
5. Click "Connect" → "Connect your application"
6. Copy the connection string (looks like: `mongodb+srv://username:password@cluster.mongodb.net/`)
7. Replace `<password>` with your actual password
8. Add database name at the end: `mongodb+srv://username:password@cluster.mongodb.net/ryuuko`

### Option B: Local MongoDB

1. Install MongoDB Community Edition for your OS
2. Start MongoDB service:
   ```bash
   # macOS (with Homebrew)
   brew services start mongodb-community

   # Linux
   sudo systemctl start mongod

   # Windows
   # MongoDB runs as a service automatically after installation
   ```
3. Your connection string will be: `mongodb://localhost:27017/ryuuko`

### Create Database Indexes (Important!)

For optimal performance with the hierarchical memory system, create these indexes:

```bash
# Connect to your MongoDB using mongosh or MongoDB Compass
# Then run these commands:

use ryuuko

# Index for sliding window queries (Level 1)
db.memory_nodes.createIndex({ "user_id": 1, "timestamp": -1 })

# Index for RAG vector search (Level 2)
# Note: Vector search index might need to be created via Atlas UI or specific driver commands
# For basic setup, the above index is sufficient for timestamp-based queries

# Index for account linking lookups
db.linked_accounts.createIndex({ "platform": 1, "platform_user_id": 1 })

# Index for user lookups
db.users.createIndex({ "email": 1 }, { unique: true })
```

## Step 5: Environment Configuration

Each component requires its own `.env` file. Create these files based on the templates below.

### A. Core API Service Configuration

Navigate to the Core API directory and create `.env`:

```bash
cd packages/ryuuko-api
```

Create the `.env` file (you can copy from `.env.example` if available):

```env
# MongoDB Connection
MONGODB_CONNECTION_STRING=mongodb://localhost:27017/ryuuko
# Or for Atlas:
# MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/ryuuko

# API Security
# Generate a secure random key (minimum 32 characters)
CORE_API_KEY=your-secure-random-api-key-at-least-32-chars-long

# LLM Provider API Keys
# You need at least ONE of these providers configured

# Google Gemini (via AI Studio)
# Get from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your-google-gemini-api-key

# PolyDevs API
# Get from: https://polydevs.uk or your provider
POLYDEVS_API_KEY=your-polydevs-api-key

# ProxyVN (for GPT models)
# Get from your provider
PROXYVN_API_KEY=your-proxyvn-api-key

# Dashboard Authentication
# Generate a secure random secret for JWT tokens (minimum 32 characters)
SECRET_KEY=your-jwt-secret-key-minimum-32-characters-long

# Server Configuration (optional)
HOST=0.0.0.0
PORT=8000
```

**Important Notes:**
- Replace all `your-*` placeholders with actual values
- Keep your API keys secure and never commit `.env` to version control
- Generate secure random keys using:
  ```bash
  # On macOS/Linux:
  openssl rand -hex 32

  # Or in Python:
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

### B. Discord Bot Configuration

Navigate to Discord bot directory and create `.env`:

```bash
cd ../discord-bot  # From packages/ryuuko-api
```

Create the `.env` file:

```env
# Discord Bot Token
# Get from: https://discord.com/developers/applications
DISCORD_TOKEN=your-discord-bot-token-here

# Core API Connection
CORE_API_URL=http://127.0.0.1:8000
# IMPORTANT: This MUST match the CORE_API_KEY from the Core API .env
CORE_API_KEY=your-secure-random-api-key-at-least-32-chars-long
```

**How to get Discord Bot Token:**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to "Bot" tab → Click "Add Bot"
4. Under "Token", click "Reset Token" and copy it
5. Enable these **Privileged Gateway Intents**:
   - Message Content Intent (required to read messages)
   - Server Members Intent (optional, for member info)
6. Go to "OAuth2" → "URL Generator"
7. Select scopes: `bot`, `applications.commands`
8. Select permissions: `Send Messages`, `Read Messages/View Channels`, `Embed Links`, `Attach Files`
9. Copy generated URL and invite bot to your server

### C. Telegram Bot Configuration

Navigate to Telegram bot directory and create `.env`:

```bash
cd ../telegram-bot  # From packages/discord-bot
```

Create the `.env` file:

```env
# Telegram Bot Token
# Get from: @BotFather on Telegram
TELEGRAM_TOKEN=your-telegram-bot-token

# Core API Connection
CORE_API_URL=http://127.0.0.1:8000
# IMPORTANT: This MUST match the CORE_API_KEY from the Core API .env
CORE_API_KEY=your-secure-random-api-key-at-least-32-chars-long
```

**How to get Telegram Bot Token:**
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow prompts to choose name and username
4. BotFather will send you the token
5. Copy the token to your `.env` file

### D. Web Dashboard Configuration

Navigate to dashboard directory and create `.env`:

```bash
cd ../dashboard  # From packages/telegram-bot
```

Create the `.env` file:

```env
# Core API URL
VITE_API_URL=http://localhost:8000
```

**Note:** For production, change this to your actual API domain.

## Step 6: Install Dashboard Dependencies (Optional)

If you're running the Web Dashboard, install Node.js dependencies:

```bash
# Make sure you're in packages/dashboard
npm install
```

This installs React, Vite, Axios, and other frontend dependencies.

## Step 7: Running the Ecosystem

You need to run each service in a **separate terminal window/tab**. Make sure your virtual environment is activated in each terminal.

### Terminal 1: Start Core API Service

```bash
# From project root (ryuuko-chatbot/)
source .venv/bin/activate  # Activate venv
python3 -m ryuuko_api
```

You should see output like:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Test it:** Open browser to `http://localhost:8000` - you should see `{"message": "Ryuuko API is running."}`

### Terminal 2: Start Discord Bot (Optional)

```bash
# From project root (ryuuko-chatbot/)
source .venv/bin/activate  # Activate venv
python3 -m discord_bot
```

You should see:
```
[OK] Discord client is ready: YourBotName (id=123456789)
```

### Terminal 3: Start Telegram Bot (Optional)

```bash
# From project root (ryuuko-chatbot/)
source .venv/bin/activate  # Activate venv
python3 -m telegram_bot
```

You should see:
```
INFO - Telegram bot is starting...
```

### Terminal 4: Start Web Dashboard (Optional)

```bash
# From project root
cd packages/dashboard
npm run dev
```

You should see:
```
  VITE v4.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

**Access it:** Open browser to `http://localhost:5173`

## Step 8: Initial Setup and Testing

### Create Dashboard Account

1. Open browser to `http://localhost:5173`
2. Click "Register"
3. Create an account with email and password
4. Login with your credentials

### Link Discord Account (if using Discord bot)

1. In Discord, send a message to your bot: `,help`
2. Bot should respond with available commands
3. Get your Discord User ID:
   - Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
   - Right-click your username → Copy ID
4. In the Web Dashboard:
   - Go to "Link Accounts" tab
   - Paste your Discord User ID
   - Click "Link Discord Account"

### Link Telegram Account (if using Telegram bot)

1. Start a chat with your Telegram bot
2. Get your Telegram User ID:
   - Send `/start` to the bot
   - The bot might show your ID, or you can use @userinfobot to get it
3. In the Web Dashboard:
   - Go to "Link Accounts" tab
   - Paste your Telegram User ID
   - Click "Link Telegram Account"

### Test AI Chat

**Discord:**
```
@YourBot Hello! How are you?
```

**Telegram:**
Send a message directly to your bot:
```
Hello! How are you?
```

The bot should respond with AI-generated text!

### Test Multimodal (Image + Text)

**Discord:**
1. Upload an image
2. Add caption: `What's in this image?`

**Telegram:**
1. Send a photo to the bot
2. Add caption: `What's in this image?`

### Test Commands

**Discord:**
```
,help          # Show available commands
,models        # List available AI models
,profile       # View your profile
,clearmemory   # Clear conversation history
```

**Telegram:**
```
/help
/profile
/clearmemory
```

## Troubleshooting

### Core API won't start

**Error:** `pymongo.errors.ServerSelectionTimeoutError`
- **Solution:** Check MongoDB is running and connection string is correct
- Test MongoDB connection:
  ```bash
  mongosh "your-connection-string"
  ```

**Error:** `ModuleNotFoundError: No module named 'ryuuko_api'`
- **Solution:** Make sure you installed with `pip install -e ./packages/ryuuko-api`
- Verify: `pip list | grep ryuuko-api`

### Discord Bot won't connect

**Error:** `discord.errors.LoginFailure: Improper token has been passed`
- **Solution:** Double-check your `DISCORD_TOKEN` in `.env`
- Make sure there are no extra spaces or quotes

**Error:** `aiohttp.client_exceptions.ClientConnectorError`
- **Solution:** Make sure Core API is running first (Terminal 1)
- Check `CORE_API_URL` in Discord bot `.env`

### Telegram Bot issues

**Error:** `telegram.error.Unauthorized: 401 Unauthorized`
- **Solution:** Check `TELEGRAM_TOKEN` is correct

### Memory/RAG not working

**Issue:** Bot doesn't remember past conversations
- **Solution:**
  1. Ensure account is linked (check Web Dashboard)
  2. Check MongoDB has `memory_nodes` collection
  3. Verify sentence-transformers is installed:
     ```bash
     python3 -c "from sentence_transformers import SentenceTransformer; print('OK')"
     ```

### Dashboard can't connect to API

**Error:** Network errors in browser console
- **Solution:**
  1. Check Core API is running on port 8000
  2. Verify `VITE_API_URL` in dashboard `.env`
  3. Check CORS settings in Core API (should allow localhost:5173)

## Development Tips

### Hot Reload

- **Core API**: Uvicorn auto-reloads on file changes
- **Dashboard**: Vite auto-reloads on file changes
- **Bots**: Need manual restart after code changes

### Logs

All services log to console. For production, consider:
```bash
python3 -m ryuuko_api > logs/api.log 2>&1 &
```

### Database GUI

Use [MongoDB Compass](https://www.mongodb.com/products/compass) to visually browse your database and verify data.

### API Documentation

FastAPI provides interactive API docs:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Next Steps

- Read `ARCHITECTURE.md` to understand the system design
- See `COMMANDS.md` for full command reference
- Check `DEPLOYMENT.md` for production deployment guide
- Review `CONTRIBUTING.md` if you want to contribute

## Security Reminders

- ✅ Never commit `.env` files to Git (already in `.gitignore`)
- ✅ Use strong, unique API keys (minimum 32 characters)
- ✅ Keep MongoDB credentials secure
- ✅ For production, use environment-specific configuration
- ✅ Regularly update dependencies for security patches

---

**Setup complete!** You now have a fully functional Ryuuko Chatbot ecosystem running locally. Happy developing! 🚀
