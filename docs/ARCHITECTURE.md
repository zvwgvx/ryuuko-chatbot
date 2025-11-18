# Architecture v3.0.0

This document provides a detailed overview of the Ryuuko Chatbot ecosystem, which is built on a **service-oriented architecture** with support for multiple client platforms.

## Core Philosophy

The project evolved from a monolithic application into a decoupled, multi-component system. This design provides:
- **Scalability**: Independent scaling of API and client services
- **Maintainability**: Clear separation of concerns and responsibilities
- **Extensibility**: Easy addition of new client platforms without modifying core logic
- **Platform Agnostic**: Unified backend serving Discord, Telegram, and Web clients

## System Components

### 1. Core API Service (`packages/ryuuko-api`)

The centralized "brain" of the entire ecosystem. This standalone **FastAPI** application handles all business logic, AI processing, and data management.

**Responsibilities:**
- **AI Processing**: Manages interactions with multiple LLM providers:
  - Google Gemini (via AI Studio)
  - PolyDevs custom models
  - ProxyVN (GPT models)
- **Hierarchical Memory Management**: Advanced 3-level memory system:
  - **Level 1**: Sliding window (10 most recent messages)
  - **Level 2**: RAG retrieval (semantic search for 10 most relevant messages)
  - **Level 3**: Contextual summarization (auto-generated conversation summaries)
- **Data Persistence**: Sole interface to MongoDB database:
  - User accounts and authentication (JWT-based)
  - Account linking (Discord/Telegram to dashboard)
  - Conversation memory (nodes with semantic vectors)
  - Model configurations and access control
  - Credit management
- **Business Logic**: User authorization, credit tracking, access levels
- **API Provision**: Secure RESTful API with streaming support

**Key Technologies:** FastAPI, Pydantic, MongoDB (PyMongo), sentence-transformers, OpenAI SDK, Google Generative AI, PyJWT, passlib

**Version:** v3.6.0

### 2. Discord Bot Client (`packages/discord-bot`)

Lightweight client for Discord platform integration.

**Responsibilities:**
- **Discord Gateway**: Connects to Discord, listens for events (`on_message`), handles commands
- **User Interaction**: Command parsing with prefix `,`
- **Payload Construction**: Processes user input and image attachments into multimodal payloads
- **API Communication**: HTTP client (httpx) sending requests to Core API
- **Response Presentation**: Streams AI responses back to Discord in real-time
- **Queue Management**: Asynchronous request queue for sequential processing

**Key Technologies:** discord.py, httpx, Pillow

**Version:** v2.0.4

### 3. Telegram Bot Client (`packages/telegram-bot`)

Lightweight client for Telegram platform integration.

**Responsibilities:**
- **Telegram Integration**: Bot API connection using python-telegram-bot
- **Message Handling**: Text messages, photos with captions, file uploads
- **Payload Construction**: Converts Telegram messages to standardized format
- **API Communication**: Streams chat completions from Core API
- **Command Support**: `/clearmemory`, `/profile`, admin commands

**Key Technologies:** python-telegram-bot, httpx, Pillow

**Version:** v1.0.1

### 4. Web Dashboard (`packages/dashboard`)

React-based web interface for user account management.

**Responsibilities:**
- **Authentication**: User registration and login (JWT tokens)
- **Account Linking**: Connect Discord/Telegram accounts to dashboard
- **Profile Management**: Update model preferences, system prompts
- **Memory Viewer**: Browse conversation history across all platforms
- **Credit Monitoring**: View credit balance and usage

**Key Technologies:** React 18, Vite, Axios, Lucide Icons

**Version:** v0.0.0

## Data Flow: Multi-Platform Chat Request

The system supports unified chat processing across all platforms (Discord, Telegram, Web). Here's the flow:

### 1. Message Reception (Client)
**Platform-specific handling:**
- **Discord**: `on_message` event listener captures messages
- **Telegram**: Message handler receives text/photo updates
- **Web Dashboard**: Not yet implemented for chat (primarily for management)

### 2. Request Queuing (Discord only)
Discord client uses `RequestQueue` for sequential processing to prevent race conditions.

### 3. Payload Construction (Client)
Each client processes input into a standardized format:
- **Text Processing**: Extract message content
- **Image Processing**:
  - Resize images to max 2048px dimension
  - Convert to JPEG (remove transparency)
  - Encode as base64 data URI
  - Validate size (max 30MB)
- **Multimodal Content**: Construct OpenAI-compatible content array with `text` and `image_url` parts

### 4. Account Linking Resolution (Core API)
**Endpoint:** `POST /api/chat/completions`

1. **Authentication**: Verify `CORE_API_KEY` header
2. **Account Lookup**: Find linked dashboard account using platform + platform_user_id
3. **User Retrieval**: Load dashboard user profile from MongoDB

### 5. Memory Preparation (MemoryManager)
The hierarchical memory system prepares context:

**Level 3 - Contextual Summary:**
- Retrieve stored conversation summary from database
- Provides high-level context of past interactions

**Level 2 - RAG Retrieval:**
- Generate embedding vector for current query using sentence-transformers
- Perform cosine similarity search in MongoDB vector index
- Retrieve 10 most semantically relevant past messages
- Exclude messages from sliding window (no duplicates)

**Level 1 - Sliding Window:**
- Fetch 10 most recent messages from memory nodes collection
- Provides immediate conversation context

**Prompt Assembly:**
```
[System Message]
├── Current Time (Vietnam timezone)
├── Contextual Summary (Level 3)
├── Long-term Relevant Memories (Level 2 - RAG)
├── Recent Conversation History (Level 1 - Sliding)
└── Custom System Prompt (user's persona/rules)

[User Message]
└── Latest user input (text + images)
```

### 6. LLM Provider Selection (Core API)
Determine provider based on model name:
- `gemini-*` → AI Studio provider
- `gpt-*` → ProxyVN provider
- Other → PolyDevs provider

### 7. AI Processing (Provider Module)
**File:** `src/providers/{polydevs|aistudio|proxyvn}.py`

1. **Forward Request**: Send prepared messages to external LLM API
2. **Stream Response**: Receive streaming text chunks
3. **Decode Content**: Handle UTF-8 encoding with surrogate pairs

### 8. Memory Storage (MemoryManager)
After receiving full response:

1. **Text Extraction**: Extract text from multimodal content
2. **Embedding Generation**: Create semantic vector using sentence-transformers
3. **Memory Node Creation**: Store in MongoDB with:
   - User ID, role (user/assistant), text content
   - Semantic vector for RAG
   - Timestamp (Vietnam timezone)
4. **Summary Update**: If 10+ new messages, trigger contextual summarization
5. **Clean Content**: Remove surrogate characters for MongoDB compatibility

### 9. Response Streaming (Core API → Client → User)
**Discord:**
- Send initial "thinking" message
- Edit message in real-time as chunks arrive
- Update with complete response

**Telegram:**
- Send typing action
- Split response by newlines
- Send each line as separate message

**Web Dashboard:**
- Future implementation for chat interface

## Database Schema

### Collections

**1. `users` (Dashboard Accounts)**
```javascript
{
  _id: ObjectId,
  email: String,
  hashed_password: String,
  model: String,              // Current AI model
  system_prompt: String,      // Custom persona
  credits: Number,
  access_level: Number        // 0=Basic, 1=Advanced, 2=Ultimate
}
```

**2. `linked_accounts` (Platform Linking)**
```javascript
{
  _id: ObjectId,
  user_id: ObjectId,          // Reference to users collection
  platform: String,           // "discord" or "telegram"
  platform_user_id: String,   // Discord/Telegram user ID
  linked_at: ISODate
}
```

**3. `memory_nodes` (Hierarchical Memory - Levels 1 & 2)**
```javascript
{
  _id: ObjectId,
  user_id: String,            // Dashboard user ID (as string)
  role: String,               // "user" or "assistant"
  text_content: String,       // Extracted text
  semantic_vector: [Float],   // Embedding for RAG (384 dimensions)
  timestamp: ISODate
}
```
**Indexes:**
- `{user_id: 1, timestamp: -1}` - For sliding window queries
- `{user_id: 1, semantic_vector: "vector"}` - Vector search for RAG

**4. `memory_summaries` (Hierarchical Memory - Level 3)**
```javascript
{
  _id: ObjectId,
  user_id: String,            // Dashboard user ID
  summary: String,            // Contextual conversation summary
  last_updated: ISODate
}
```

**5. `models` (Available AI Models)**
```javascript
{
  _id: ObjectId,
  name: String,               // Model identifier
  cost: Number,               // Credit cost per use
  access_level: Number        // Minimum access level required
}
```

## Security Architecture

### Authentication Flow

**Dashboard (JWT):**
1. User registers/logs in via `/api/auth/register` or `/api/auth/login`
2. Server validates credentials (bcrypt password hashing)
3. Server issues JWT token with user ID
4. Client includes JWT in `Authorization: Bearer <token>` header
5. Protected endpoints use `get_current_user` dependency

**Bot Clients (API Key):**
1. Clients include `X-API-Key` header with `CORE_API_KEY`
2. Endpoint validates key matches environment variable
3. Dependency: `verify_bot_api_key`

### Access Control

**User Authorization:**
- Admin commands require Discord bot owner check
- Model access based on user's `access_level` vs model's required level
- Credit deduction on each API call (not yet implemented)

**Rate Limiting:**
- Discord: Request queue prevents spam
- Telegram: Built-in rate limiting from python-telegram-bot
- API: No explicit rate limiting (future enhancement)

## Scalability Considerations

**Horizontal Scaling:**
- Core API: Stateless design allows multiple instances behind load balancer
- Bot Clients: Single instance per Discord/Telegram bot token
- Database: MongoDB supports replication and sharding

**Performance Optimizations:**
- **Streaming Responses**: Reduces perceived latency
- **Vector Indexing**: Fast similarity search for RAG
- **Efficient Memory Management**: Only retrieve relevant context
- **Connection Pooling**: MongoDB connection reuse

**Resource Usage:**
- **Memory**: Sentence transformer model (~400MB RAM)
- **Storage**: Growing memory nodes collection (consider TTL or archiving)
- **Network**: Streaming reduces peak bandwidth

## Future Enhancements

1. **Web Chat Interface**: Real-time chat in dashboard
2. **Credit Deduction**: Actual credit consumption per API call
3. **Advanced RAG**: Hybrid search (semantic + keyword)
4. **Multi-Modal Memory**: Store and retrieve image context
5. **Conversation Threads**: Separate contexts for different topics
6. **Analytics Dashboard**: Usage statistics and insights
7. **Rate Limiting**: API-level request throttling
8. **Caching Layer**: Redis for frequently accessed data
