# Ryuuko Chatbot

A modular, high-performance AI chatbot ecosystem built on a modern service-oriented architecture. The system features a powerful **Core API Service** that handles all AI processing and data management, with support for multiple client platforms including **Discord**, **Telegram**, and a **Web Dashboard**.

## Key Features

### Architecture
- **Service-Oriented Architecture**: Clean separation between backend logic and client interfaces
  - **Core API Service** (`ryuuko-api`): Standalone FastAPI backend managing all business logic, database operations (MongoDB), and LLM provider communication
  - **Multi-Platform Clients**: Lightweight clients for Discord, Telegram, and Web that communicate with the Core API

### Advanced Memory System
- **3-Level Hierarchical Memory** with intelligent context management:
  - **Level 1 - Sliding Window**: 10 most recent messages for immediate context
  - **Level 2 - RAG Retrieval**: Semantic search retrieving 10 most relevant past conversations using vector embeddings
  - **Level 3 - Contextual Summarization**: High-level conversation summaries automatically generated and updated
- **Semantic Search**: Uses sentence-transformers for vector embeddings and similarity matching
- **Automatic Summarization**: Conversation summaries updated every 10 messages

### AI Capabilities
- **Modular Provider System**: Seamless switching between multiple LLM backends:
  - Google Gemini (via AI Studio)
  - PolyDevs custom models
  - ProxyVN (GPT models)
- **Multimodal Conversations**: Full support for contextual image analysis with text prompts
- **Custom System Prompts**: Per-user AI personas and behavior customization

### User Management
- **Account Linking**: Unified user accounts across Discord, Telegram, and Web Dashboard
- **Credit System**: Granular usage tracking and credit management
- **Access Levels**: Multi-tier access control (Basic, Advanced, Ultimate)
- **Web Dashboard**: Full-featured React dashboard for account management and monitoring

## Getting Started

### Prerequisites

- **Python 3.11+** (recommended: Python 3.13)
- **Git**
- **MongoDB** database instance (local or cloud-hosted like MongoDB Atlas)
- **Node.js 18+** (only if running the Web Dashboard)

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/zvwgvx/ryuuko-chatbot
   cd ryuuko-chatbot
   ```

2. **Set up a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**

   Install the packages you need in editable mode:

   ```bash
   # Core API (required)
   pip install -e ./packages/ryuuko-api

   # Discord bot client (optional)
   pip install -e ./packages/discord-bot

   # Telegram bot client (optional)
   pip install -e ./packages/telegram-bot
   ```

### Configuration

Each component requires its own `.env` file. See `docs/SETUP.md` for detailed configuration instructions.

#### 1. Core API Service (`packages/ryuuko-api/.env`)

**Required environment variables:**
```env
# MongoDB Connection
MONGODB_CONNECTION_STRING=mongodb://localhost:27017/ryuuko

# API Security
CORE_API_KEY=your-secure-random-key-here

# LLM Provider API Keys (configure at least one)
GEMINI_API_KEY=your-gemini-api-key
POLYDEVS_API_KEY=your-polydevs-api-key
PROXYVN_API_KEY=your-proxyvn-api-key

# JWT Secret for Dashboard Authentication
SECRET_KEY=your-jwt-secret-key
```

#### 2. Discord Bot (`packages/discord-bot/.env`)

```env
DISCORD_TOKEN=your-discord-bot-token
CORE_API_URL=http://127.0.0.1:8000
CORE_API_KEY=your-secure-random-key-here  # Must match Core API
```

#### 3. Telegram Bot (`packages/telegram-bot/.env`)

```env
TELEGRAM_TOKEN=your-telegram-bot-token
CORE_API_URL=http://127.0.0.1:8000
CORE_API_KEY=your-secure-random-key-here  # Must match Core API
```

#### 4. Web Dashboard (`packages/dashboard/.env`)

```env
VITE_API_URL=http://localhost:8000
```

### Running the System

The ecosystem consists of independent services. Run the ones you need:

**Core API Service (required):**
```bash
python3 -m ryuuko_api
```

**Discord Bot (optional):**
```bash
python3 -m discord_bot
```

**Telegram Bot (optional):**
```bash
python3 -m telegram_bot
```

**Web Dashboard (optional):**
```bash
cd packages/dashboard
npm install
npm run dev
```

### Docker Deployment

Build and run individual services using Docker:

```bash
# Build Core API
docker build --build-arg PACKAGE_NAME=ryuuko-api -t ryuuko-api .

# Build Discord Bot
docker build --build-arg PACKAGE_NAME=discord-bot -t ryuuko-discord-bot .

# Run with environment variables
docker run -d --env-file packages/ryuuko-api/.env ryuuko-api
```

## Usage

### Discord Bot

Users interact with the bot through Discord commands (prefix: `,`):

- **`.help`** - Display available commands
- **`.ping`** - Check bot latency
- **`.model <name>`** - Switch AI model
- **`.models`** - List available models
- **`.profile`** - View your profile and settings
- **`.clearmemory`** - Clear conversation history

**Admin commands** (owner only):
- **`.auth <user>`** - Authorize a user
- **`.addcredit <user> <amount>`** - Add credits to user
- **`.addmodel <name> <cost> <level>`** - Add new AI model

See `docs/COMMANDS.md` for the complete command reference.

### Telegram Bot

Users can chat directly with the bot on Telegram:
- Send text messages for AI conversations
- Send images with captions for multimodal analysis
- Use `/clearmemory` to reset conversation history
- Use `/profile` to view account information

### Web Dashboard

Access the dashboard at `http://localhost:5173` (dev mode):
1. **Register/Login** - Create an account or sign in
2. **Link Accounts** - Connect your Discord/Telegram accounts
3. **Manage Settings** - Configure AI model, system prompts, view credits
4. **View Memory** - Browse conversation history across all platforms

## Project Structure

```
ryuuko-chatbot/
├── packages/
│   ├── ryuuko-api/          # Core API Service (FastAPI)
│   │   ├── src/
│   │   │   ├── api/         # API endpoints (auth, users, admin, memory)
│   │   │   ├── models/      # Database models
│   │   │   ├── providers/   # LLM provider integrations
│   │   │   ├── memory_manager.py    # Hierarchical memory system
│   │   │   ├── database.py          # MongoDB operations
│   │   │   └── main.py              # FastAPI application
│   │   ├── config/          # Configuration files
│   │   └── instructions/    # System prompts (English/Vietnamese)
│   │
│   ├── discord-bot/         # Discord client
│   │   └── src/
│   │       ├── commands/    # Command handlers
│   │       ├── events/      # Event listeners
│   │       └── utils/       # Queue, logging, embeds
│   │
│   ├── telegram-bot/        # Telegram client
│   │   └── src/
│   │       ├── commands/    # Command handlers
│   │       └── api_client.py
│   │
│   └── dashboard/           # Web Dashboard (React + Vite)
│       └── src/
│           └── components/  # React components
│
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md      # System architecture details
│   ├── SETUP.md            # Detailed setup guide
│   ├── COMMANDS.md         # Command reference
│   └── DEPLOYMENT.md       # Production deployment guide
│
├── scripts/                # Utility scripts
└── Dockerfile             # Multi-stage Docker build
```

## Architecture Overview

The system uses a **service-oriented architecture** with clear separation of concerns:

1. **Core API** - Centralized backend handling:
   - AI processing with multiple LLM providers
   - Hierarchical memory management (sliding window + RAG + summarization)
   - User authentication and authorization
   - Credit and access control
   - Database operations (MongoDB)

2. **Client Applications** - Platform-specific interfaces:
   - Discord bot (discord.py)
   - Telegram bot (python-telegram-bot)
   - Web dashboard (React)

3. **Communication** - All clients communicate with the Core API via:
   - RESTful HTTP endpoints
   - API key authentication
   - Streaming responses for real-time AI output

See `docs/ARCHITECTURE.md` for detailed architecture documentation.

## Documentation

- **[Setup Guide](docs/SETUP.md)** - Detailed installation and configuration instructions
- **[Architecture](docs/ARCHITECTURE.md)** - System design and data flow
- **[Commands](docs/COMMANDS.md)** - Complete command reference for Discord bot
- **[Deployment](docs/DEPLOYMENT.md)** - Production deployment with systemd and Docker
- **[Contributing](CONTRIBUTING.md)** - Guidelines for contributing to the project
- **[Security](SECURITY.md)** - Security policies and best practices

## Technologies

### Backend
- **FastAPI** - Modern, high-performance web framework
- **MongoDB** - NoSQL database for flexible data storage
- **Sentence Transformers** - Semantic embedding for RAG
- **OpenAI SDK** - Unified interface for LLM providers
- **Google Generative AI** - Gemini model integration

### Clients
- **discord.py** - Discord bot framework
- **python-telegram-bot** - Telegram bot framework
- **React + Vite** - Modern web dashboard
- **httpx** - Async HTTP client for API communication

### Infrastructure
- **Docker** - Containerization for easy deployment
- **Uvicorn** - ASGI server for FastAPI
- **python-dotenv** - Environment variable management

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Reporting bugs
- Suggesting features
- Setting up development environment
- Code style and testing requirements
- Submitting pull requests

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Security

For security concerns, please refer to our [Security Policy](SECURITY.md). Do not report security vulnerabilities through public GitHub issues.

## Support

- **Documentation**: Check the `docs/` directory for detailed guides
- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/zvwgvx/ryuuko-chatbot/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/zvwgvx/ryuuko-chatbot/discussions)

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by various LLM providers (Google Gemini, PolyDevs, ProxyVN)
- UI components inspired by modern dashboard designs
- Memory system inspired by hierarchical memory research

---

**Current Version**: v2.0+ (Service-Oriented Architecture)

**Maintainer**: [Zang Vũ](https://github.com/zvwgvx) (zvwgvx@polydevs.uk)
