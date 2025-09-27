#!/usr/bin/env python3
# coding: utf-8
# database.py - PostgreSQL VERSION - FIXED CIRCULAR IMPORT

import logging
import json
import os
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2 import pool
from contextlib import contextmanager
import tiktoken
import time

logger = logging.getLogger("database")


def _load_config():
    """Load configuration directly from config.json to avoid circular import"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Try alternative path
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found at {config_path}")
            return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        return {}


# Load config directly
CONFIG = _load_config()

# Get PostgreSQL configuration with defaults
POSTGRESQL_HOST = CONFIG.get("POSTGRESQL_HOST", "localhost")
POSTGRESQL_PORT = CONFIG.get("POSTGRESQL_PORT", "5432")
POSTGRESQL_DATABASE = CONFIG.get("POSTGRESQL_DATABASE", "polydevsdb")
POSTGRESQL_USER = CONFIG.get("POSTGRESQL_USER")
POSTGRESQL_PASSWORD = CONFIG.get("POSTGRESQL_PASSWORD")


class PostgreSQLStore:
    """PostgreSQL storage manager for Discord OpenAI proxy"""

    def __init__(self):
        """Initialize PostgreSQL connection using config.json"""
        self.connection_pool = None

        # Validate required config
        if not POSTGRESQL_USER or not POSTGRESQL_PASSWORD:
            raise RuntimeError("POSTGRESQL_USER and POSTGRESQL_PASSWORD must be provided in config.json")

        # Use a more reliable tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

        self._connect()
        self._create_tables()
        self._initialize_default_models()

    def _connect(self):
        """Establish PostgreSQL connection pool with Supabase support"""
        try:
            # Supabase requires SSL and specific timeouts
            connection_params = {
                "host": POSTGRESQL_HOST,
                "port": int(POSTGRESQL_PORT),
                "database": POSTGRESQL_DATABASE,
                "user": POSTGRESQL_USER,
                "password": POSTGRESQL_PASSWORD,
                "cursor_factory": RealDictCursor,
                "sslmode": "require",  # Supabase requires SSL
                "connect_timeout": 10,
                "application_name": "ryuuko_chatbot"
            }

            logger.info(f"Attempting to connect to Supabase PostgreSQL at {POSTGRESQL_HOST}:{POSTGRESQL_PORT}")

            # Create connection pool with Supabase-specific settings
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                1,  # Min connections
                10,  # Max connections (reduced for Supabase)
                **connection_params
            )

            # Test connection
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version()")
                    version = cur.fetchone()
                    logger.info(f"Connected to: {version}")

            logger.info(f"Successfully connected to Supabase PostgreSQL: {POSTGRESQL_DATABASE}@{POSTGRESQL_HOST}")

        except psycopg2.OperationalError as e:
            if "could not translate host name" in str(e):
                logger.error("DNS resolution failed. Please check:")
                logger.error("1. Internet connection")
                logger.error("2. Supabase host name is correct")
                logger.error("3. Your firewall/network allows outbound connections to port 5432")
            elif "authentication failed" in str(e):
                logger.error("Authentication failed. Please check:")
                logger.error("1. Username and password are correct")
                logger.error("2. Database name is correct")
            else:
                logger.error(f"PostgreSQL connection failed: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error connecting to PostgreSQL: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def _create_tables(self):
        """Create necessary tables and indexes"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # User configs table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS user_configs (
                            user_id BIGINT PRIMARY KEY,
                            model VARCHAR(255) DEFAULT 'gemini-2.5-flash',
                            system_prompt TEXT DEFAULT 'Tên của bạn là Ryuuko (nữ), nói tiếng việt',
                            credit INTEGER DEFAULT 0,
                            access_level INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # User memory table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS user_memory (
                            user_id BIGINT PRIMARY KEY,
                            messages JSONB DEFAULT '[]'::jsonb,
                            message_count INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Authorized users table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS authorized_users (
                            user_id BIGINT PRIMARY KEY,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Supported models table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS supported_models (
                            model_name VARCHAR(255) PRIMARY KEY,
                            credit_cost INTEGER DEFAULT 0,
                            access_level INTEGER DEFAULT 0,
                            is_default BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Profile models table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS profile_models (
                            name VARCHAR(255) PRIMARY KEY,
                            base_model VARCHAR(255),
                            sys_prompt TEXT,
                            credit_cost INTEGER DEFAULT 0,
                            access_level INTEGER DEFAULT 0,
                            is_live BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Create indexes
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_memory_updated ON user_memory(user_id, updated_at DESC)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_configs_user ON user_configs(user_id)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_authorized_users ON authorized_users(user_id)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_supported_models ON supported_models(model_name)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_profile_models ON profile_models(name)")

                    conn.commit()
                    logger.info("PostgreSQL tables and indexes created successfully")

        except Exception as e:
            logger.exception(f"Error creating tables: {e}")
            raise

    def _initialize_default_models(self):
        """Initialize default supported models if table is empty"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as count FROM supported_models")
                    count = cur.fetchone()['count']

                    if count == 0:
                        default_models = [
                            ("gemini-2.5-flash", 10, 0, True),
                            ("gemini-2.5-pro", 50, 0, True),
                            ("gpt-3.5-turbo", 200, 0, True),
                            ("gpt-5", 700, 1, True)
                        ]

                        cur.executemany("""
                            INSERT INTO supported_models (model_name, credit_cost, access_level, is_default)
                            VALUES (%s, %s, %s, %s) ON CONFLICT (model_name) DO NOTHING
                        """, default_models)

                        conn.commit()
                        logger.info("Default models initialized in PostgreSQL")

        except Exception as e:
            logger.exception(f"Error initializing default models: {e}")

    # =====================================
    # MEMORY METHODS - FIXED VERSION
    # =====================================

    def get_user_messages(self, user_id: int) -> List[Dict[str, str]]:
        """Get user's conversation history with strong consistency"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT messages
                        FROM user_memory
                        WHERE user_id = %s
                    """, (user_id,))

                    result = cur.fetchone()
                    if result and result['messages']:
                        messages = result['messages']
                        logger.debug(f"Retrieved {len(messages)} messages for user {user_id}")
                        return messages

            logger.debug(f"No messages found for user {user_id}")
            return []

        except Exception as e:
            logger.exception(f"Error getting messages for user {user_id}: {e}")
            return []

    def add_message(self, user_id: int, message: Dict[str, str], max_messages: int = 25, max_tokens: int = 4000):
        """Add message to user's conversation history - FIXED VERSION"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Lock the row for update to prevent race conditions
                    cur.execute("""
                        SELECT messages
                        FROM user_memory
                        WHERE user_id = %s
                        FOR UPDATE
                    """, (user_id,))

                    result = cur.fetchone()
                    current_messages = result['messages'] if result else []

                    # Add new message
                    updated_messages = current_messages + [message]

                    # Apply limits
                    updated_messages = self._apply_memory_limits(updated_messages, max_messages, max_tokens)

                    # Upsert the messages
                    cur.execute("""
                        INSERT INTO user_memory (user_id, messages, message_count, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP) 
                        ON CONFLICT (user_id) 
                        DO UPDATE SET
                            messages = EXCLUDED.messages,
                            message_count = EXCLUDED.message_count,
                            updated_at = CURRENT_TIMESTAMP
                    """, (user_id, Json(updated_messages), len(updated_messages)))

                    conn.commit()

            logger.info(f"Successfully added message for user {user_id}. Total messages: {len(updated_messages)}")
            return True

        except Exception as e:
            logger.exception(f"Error adding message for user {user_id}: {e}")
            return False

    def _apply_memory_limits(self, messages: List[Dict[str, str]], max_messages: int, max_tokens: int) -> List[Dict[str, str]]:
        """Apply message count and token limits while preserving conversation flow"""
        if not messages:
            return messages

        # First apply message count limit
        if len(messages) > max_messages:
            # Keep the most recent messages
            messages = messages[-max_messages:]

        # Then apply token limit
        total_tokens = 0
        token_counts = []

        # Calculate tokens for each message
        for msg in messages:
            try:
                tokens = len(self.tokenizer.encode(msg.get("content", "")))
                token_counts.append(tokens)
                total_tokens += tokens
            except Exception as e:
                logger.warning(f"Error calculating tokens for message: {e}")
                token_counts.append(100)  # Fallback estimate
                total_tokens += 100

        # If over token limit, remove oldest messages
        if total_tokens > max_tokens:
            final_messages = []
            current_tokens = 0

            # Work backwards to keep most recent messages within token limit
            for i in range(len(messages) - 1, -1, -1):
                msg_tokens = token_counts[i]
                if current_tokens + msg_tokens <= max_tokens:
                    final_messages.insert(0, messages[i])
                    current_tokens += msg_tokens
                else:
                    break

            logger.debug(f"Trimmed messages from {len(messages)} to {len(final_messages)} due to token limit")
            return final_messages

        return messages

    def clear_user_memory(self, user_id: int) -> bool:
        """Clear user's conversation history with transaction"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM user_memory WHERE user_id = %s", (user_id,))
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as e:
            logger.exception(f"Error clearing memory for user {user_id}: {e}")
            return False

    def remove_last_message(self, user_id: int) -> bool:
        """Remove the last message from user's conversation history"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT messages
                        FROM user_memory
                        WHERE user_id = %s
                        FOR UPDATE
                    """, (user_id,))

                    result = cur.fetchone()
                    if not result or not result['messages']:
                        return False

                    messages = result['messages']
                    if not messages:
                        return False

                    # Remove last message
                    messages = messages[:-1]

                    # Update document
                    cur.execute("""
                        UPDATE user_memory
                        SET messages = %s,
                            message_count = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                    """, (Json(messages), len(messages), user_id))

                    conn.commit()
                    return cur.rowcount > 0

        except Exception as e:
            logger.exception(f"Error removing last message for user {user_id}: {e}")
            return False

    # =====================================
    # USER CONFIG METHODS
    # =====================================

    def get_user_config(self, user_id: int) -> Dict[str, Any]:
        """Get user configuration"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT model, system_prompt, credit, access_level
                        FROM user_configs
                        WHERE user_id = %s
                    """, (user_id,))

                    result = cur.fetchone()
                    if result:
                        user_model = result['model']
                        if not self.model_exists(user_model):
                            supported_models = self.get_supported_models()
                            if supported_models:
                                user_model = next(iter(supported_models))
                                self.set_user_config(user_id, model=user_model)
                            else:
                                user_model = "gemini-2.5-flash"

                        return {
                            "model": user_model,
                            "system_prompt": result['system_prompt'],
                            "credit": result['credit'],
                            "access_level": result['access_level']
                        }

                    # Default values
                    return {
                        "model": "gemini-2.5-flash",
                        "system_prompt": "Tên của bạn là Ryuuko (nữ), nói tiếng việt",
                        "credit": 0,
                        "access_level": 0
                    }

        except Exception as e:
            logger.exception(f"Error getting user config for {user_id}: {e}")
            return {
                "model": "gemini-2.5-flash",
                "system_prompt": "Tên của bạn là Ryuuko (nữ), nói tiếng việt",
                "credit": 0,
                "access_level": 0
            }

    def set_user_config(self, user_id: int, model: Optional[str] = None, system_prompt: Optional[str] = None) -> bool:
        """Set user configuration"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    if model is not None and not self.model_exists(model):
                        logger.warning(f"Attempt to set non-existent model {model} for user {user_id}")
                        return False

                    # Check if user exists
                    cur.execute("SELECT 1 FROM user_configs WHERE user_id = %s", (user_id,))
                    exists = cur.fetchone() is not None

                    if exists:
                        # Update existing record
                        updates = []
                        params = []

                        if model is not None:
                            updates.append("model = %s")
                            params.append(model)
                        if system_prompt is not None:
                            updates.append("system_prompt = %s")
                            params.append(system_prompt)

                        if updates:
                            updates.append("updated_at = CURRENT_TIMESTAMP")
                            params.append(user_id)

                            cur.execute(f"""
                                UPDATE user_configs 
                                SET {", ".join(updates)}
                                WHERE user_id = %s
                            """, params)
                    else:
                        # Insert new record
                        cur.execute("""
                            INSERT INTO user_configs (user_id, model, system_prompt)
                            VALUES (%s, %s, %s)
                        """, (
                            user_id,
                            model if model is not None else "gemini-2.5-flash",
                            system_prompt if system_prompt is not None else "Tên của bạn là Ryuuko (nữ), nói tiếng việt"
                        ))

                    conn.commit()
                    return True

        except Exception as e:
            logger.exception(f"Error setting user config for {user_id}: {e}")
            return False

    def get_user_model(self, user_id: int) -> str:
        """Get user's preferred model"""
        config = self.get_user_config(user_id)
        return config["model"]

    def get_user_system_prompt(self, user_id: int) -> str:
        """Get user's system prompt"""
        config = self.get_user_config(user_id)
        return config["system_prompt"]

    def get_user_system_message(self, user_id: int) -> Dict[str, str]:
        """Get system message in OpenAI format"""
        return {
            "role": "system",
            "content": self.get_user_system_prompt(user_id)
        }

    # =====================================
    # SUPPORTED MODELS METHODS
    # =====================================

    def get_supported_models(self) -> Set[str]:
        """Get set of supported model names"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT model_name FROM supported_models")
                    return {row['model_name'] for row in cur.fetchall()}
        except Exception as e:
            logger.exception(f"Error getting supported models: {e}")
            return {"gemini-2.5-flash", "gemini-2.5-pro", "gpt-3.5-turbo", "gpt-5"}

    def model_exists(self, model_name: str) -> bool:
        """Check if a model exists in supported models or profile models"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check regular models
                    cur.execute("SELECT 1 FROM supported_models WHERE model_name = %s", (model_name,))
                    if cur.fetchone():
                        return True

                    # Check profile models
                    cur.execute("SELECT 1 FROM profile_models WHERE name = %s", (model_name,))
                    return cur.fetchone() is not None

        except Exception as e:
            logger.exception(f"Error checking if model {model_name} exists: {e}")
            return False

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a model"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT *
                        FROM supported_models
                        WHERE model_name = %s
                    """, (model_name,))
                    return cur.fetchone()
        except Exception as e:
            logger.exception(f"Error getting model info for {model_name}: {e}")
            return None

    def list_all_models(self) -> List[Dict[str, Any]]:
        """Get list of all models with their details"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM supported_models ORDER BY created_at")
                    return cur.fetchall()
        except Exception as e:
            logger.exception(f"Error listing all models: {e}")
            return []

    def add_supported_model(self, model_name: str, credit_cost: int = 1, access_level: int = 0) -> tuple[bool, str]:
        """Add a new supported model"""
        try:
            model_name = model_name.strip()
            if not model_name:
                return False, "Model name cannot be empty"

            if credit_cost < 0:
                return False, "Credit cost cannot be negative"

            if access_level not in [0, 1, 2, 3]:
                return False, "Access level must be 0, 1, 2, or 3"

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if model already exists
                    cur.execute("SELECT 1 FROM supported_models WHERE model_name = %s", (model_name,))
                    if cur.fetchone():
                        return False, f"Model '{model_name}' already exists"

                    cur.execute("""
                        INSERT INTO supported_models (model_name, credit_cost, access_level, is_default)
                        VALUES (%s, %s, %s, FALSE)
                    """, (model_name, credit_cost, access_level))

                    conn.commit()
                    return True, f"Successfully added model '{model_name}' (Cost: {credit_cost}, Level: {access_level})"

        except Exception as e:
            logger.exception(f"Error adding model {model_name}: {e}")
            return False, f"Database error: {e}"

    def remove_supported_model(self, model_name: str) -> tuple[bool, str]:
        """Remove a supported model"""
        try:
            model_name = model_name.strip()
            if not model_name:
                return False, "Model name cannot be empty"

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if model exists
                    cur.execute("SELECT is_default FROM supported_models WHERE model_name = %s", (model_name,))
                    result = cur.fetchone()

                    if not result:
                        return False, f"Model '{model_name}' does not exist"

                    if result['is_default']:
                        return False, f"Cannot remove default model '{model_name}'"

                    # Check if users are using this model
                    cur.execute("SELECT COUNT(*) as count FROM user_configs WHERE model = %s", (model_name,))
                    users_count = cur.fetchone()['count']

                    if users_count > 0:
                        return False, f"Cannot remove model '{model_name}' - {users_count} user(s) are currently using it"

                    # Delete model
                    cur.execute("DELETE FROM supported_models WHERE model_name = %s", (model_name,))
                    conn.commit()

                    if cur.rowcount > 0:
                        return True, f"Successfully removed model '{model_name}'"
                    return False, "Failed to remove model from database"

        except Exception as e:
            logger.exception(f"Error removing model {model_name}: {e}")
            return False, f"Database error: {e}"

    def edit_supported_model(self, model_name: str, credit_cost: int = None, access_level: int = None) -> tuple[bool, str]:
        """Edit an existing model's settings"""
        try:
            model_name = model_name.strip()
            if not model_name:
                return False, "Model name cannot be empty"

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if model exists
                    cur.execute("SELECT 1 FROM supported_models WHERE model_name = %s", (model_name,))
                    if not cur.fetchone():
                        return False, f"Model '{model_name}' does not exist"

                    updates = []
                    params = []

                    if credit_cost is not None:
                        if credit_cost < 0:
                            return False, "Credit cost cannot be negative"
                        updates.append("credit_cost = %s")
                        params.append(credit_cost)

                    if access_level is not None:
                        if access_level not in [0, 1, 2, 3]:
                            return False, "Access level must be 0, 1, 2, or 3"
                        updates.append("access_level = %s")
                        params.append(access_level)

                    if updates:
                        updates.append("updated_at = CURRENT_TIMESTAMP")
                        params.append(model_name)

                        cur.execute(f"""
                            UPDATE supported_models 
                            SET {", ".join(updates)}
                            WHERE model_name = %s
                        """, params)

                        conn.commit()

                        if cur.rowcount > 0:
                            return True, f"Successfully updated model '{model_name}'"

                    return False, "No changes were made"

        except Exception as e:
            logger.exception(f"Error editing model {model_name}: {e}")
            return False, f"Database error: {e}"

    # =====================================
    # AUTHORIZED USERS METHODS
    # =====================================

    def get_authorized_users(self) -> Set[int]:
        """Get set of authorized user IDs"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT user_id FROM authorized_users")
                    return {row['user_id'] for row in cur.fetchall()}
        except Exception as e:
            logger.exception(f"Error getting authorized users: {e}")
            return set()

    def add_authorized_user(self, user_id: int) -> bool:
        """Add user to authorized list"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO authorized_users (user_id)
                        VALUES (%s) ON CONFLICT (user_id) DO NOTHING
                    """, (user_id,))
                    conn.commit()
                    return True
        except Exception as e:
            logger.exception(f"Error adding authorized user {user_id}: {e}")
            return False

    def remove_authorized_user(self, user_id: int) -> bool:
        """Remove user from authorized list"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM authorized_users WHERE user_id = %s", (user_id,))
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as e:
            logger.exception(f"Error removing authorized user {user_id}: {e}")
            return False

    def is_user_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT EXISTS(SELECT 1 FROM authorized_users WHERE user_id = %s)", (user_id,))
                    return cur.fetchone()['exists']
        except Exception as e:
            logger.exception(f"Error checking authorization for user {user_id}: {e}")
            return False

    # =====================================
    # USER LEVEL AND CREDIT METHODS
    # =====================================

    def set_user_level(self, user_id: int, level: int) -> bool:
        """Set user access level"""
        try:
            if level not in [0, 1, 2, 3]:
                return False

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO user_configs (user_id, access_level, updated_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP) 
                        ON CONFLICT (user_id)
                        DO UPDATE SET
                            access_level = EXCLUDED.access_level,
                            updated_at = CURRENT_TIMESTAMP
                    """, (user_id, level))
                    conn.commit()
                    return True

        except Exception as e:
            logger.exception(f"Error setting level for user {user_id}: {e}")
            return False

    def add_user_credit(self, user_id: int, amount: int) -> tuple[bool, int]:
        """Add credit to user balance"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO user_configs (user_id, credit)
                        VALUES (%s, %s) 
                        ON CONFLICT (user_id)
                        DO UPDATE SET credit = user_configs.credit + EXCLUDED.credit
                        RETURNING credit
                    """, (user_id, amount))

                    result = cur.fetchone()
                    conn.commit()

                    if result:
                        return True, result['credit']
                    return False, 0

        except Exception as e:
            logger.exception(f"Error adding credit for user {user_id}: {e}")
            return False, 0

    def deduct_user_credit(self, user_id: int, amount: int) -> tuple[bool, int]:
        """Deduct credit from user balance"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE user_configs
                        SET credit = credit - %s
                        WHERE user_id = %s
                          AND credit >= %s 
                        RETURNING credit
                    """, (amount, user_id, amount))

                    result = cur.fetchone()
                    conn.commit()

                    if result:
                        return True, result['credit']
                    return False, 0

        except Exception as e:
            logger.exception(f"Error deducting credit for user {user_id}: {e}")
            return False, 0

    # =====================================
    # PROFILE MODEL METHODS
    # =====================================

    def add_profile_model(self, name: str) -> tuple[bool, str]:
        """Add a new profile model with default values"""
        try:
            name = name.strip()
            if not name:
                return False, "Profile model name cannot be empty"

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if profile already exists
                    cur.execute("SELECT 1 FROM profile_models WHERE name = %s", (name,))
                    if cur.fetchone():
                        return False, f"Profile model '{name}' already exists"

                    cur.execute("""
                        INSERT INTO profile_models (name, credit_cost, access_level, is_live)
                        VALUES (%s, 0, 0, FALSE)
                    """, (name,))

                    conn.commit()
                    return True, f"Successfully created profile model '{name}'. Use ;edit pmodel to configure settings."

        except Exception as e:
            logger.exception(f"Error adding profile model {name}: {e}")
            return False, f"Database error: {e}"

    def get_profile_model_details(self, name: str) -> tuple[bool, str]:
        """Get detailed info about a profile model"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM profile_models WHERE name = %s", (name,))
                    profile = cur.fetchone()

                    if not profile:
                        return False, f"Profile model '{name}' does not exist"

                    # Format details
                    details = [
                        f"**Profile Model: `{name}`**",
                        f"Base Model: `{profile['base_model'] or 'Not set'}`",
                        f"Cost: {profile['credit_cost']} credits",
                        f"Level: {profile['access_level']}",
                        f"Live: {'✅' if profile['is_live'] else '❌'}"
                    ]

                    # Add system prompt at the end
                    sys_prompt = profile.get('sys_prompt')
                    if sys_prompt:
                        details.append("\n**System Prompt:**")
                        details.append(f"`{sys_prompt}`")

                    return True, "\n".join(details)

        except Exception as e:
            logger.exception(f"Error getting profile model details {name}: {e}")
            return False, f"Error: {e}"

    def edit_profile_model(self, name: str, field: str, value: Any) -> tuple[bool, str]:
        """Edit a profile model field"""
        try:
            name = name.strip()
            if not name:
                return False, "Profile model name cannot be empty"

            valid_fields = ["base_model", "sys_prompt", "credit_cost", "access_level", "is_live"]
            if field not in valid_fields:
                return False, f"Invalid field '{field}'. Valid fields: {', '.join(valid_fields)}"

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if profile exists
                    cur.execute("SELECT 1 FROM profile_models WHERE name = %s", (name,))
                    if not cur.fetchone():
                        return False, f"Profile model '{name}' does not exist"

                    # Validate and convert value based on field
                    if field in ["credit_cost", "access_level"]:
                        try:
                            value = int(value)
                            if field == "access_level" and value not in [0, 1, 2, 3]:
                                return False, "Access level must be 0, 1, 2, or 3"
                            if field == "credit_cost" and value < 0:
                                return False, "Credit cost cannot be negative"
                        except ValueError:
                            return False, f"{field} must be an integer"
                    elif field == "is_live":
                        value = str(value).lower() in ['true', '1', 'yes']

                    # Update field
                    cur.execute(f"""
                        UPDATE profile_models 
                        SET {field} = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE name = %s
                    """, (value, name))

                    conn.commit()

                    if cur.rowcount > 0:
                        return True, f"Successfully updated {field} for profile model '{name}'"
                    return False, "No changes were made"

        except Exception as e:
            logger.exception(f"Error editing profile model {name}: {e}")
            return False, f"Database error: {e}"

    def get_profile_model(self, name: str) -> Optional[Dict[str, Any]]:
        """Get profile model details"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM profile_models WHERE name = %s", (name,))
                    return cur.fetchone()
        except Exception as e:
            logger.exception(f"Error getting profile model {name}: {e}")
            return None

    def list_profile_models(self) -> List[Dict[str, Any]]:
        """List all profile models"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM profile_models ORDER BY name")
                    return cur.fetchall()
        except Exception as e:
            logger.exception("Error listing profile models")
            return []

    def delete_profile_model(self, name: str) -> bool:
        """Delete a profile model"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM profile_models WHERE name = %s", (name,))
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as e:
            logger.exception(f"Error deleting profile model {name}: {e}")
            return False

    def get_users_using_model(self, model_name: str) -> List[int]:
        """Get list of user IDs currently using a specific model"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT user_id FROM user_configs WHERE model = %s", (model_name,))
                    return [row['user_id'] for row in cur.fetchall()]
        except Exception as e:
            logger.exception(f"Error getting users for model {model_name}: {e}")
            return []

    def close(self):
        """Close PostgreSQL connection pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("PostgreSQL connection pool closed")


# =====================================
# SINGLETON PATTERN - DELAYED INIT
# =====================================

# Global store instance
_postgresql_store: Optional[PostgreSQLStore] = None


def get_postgresql_store() -> PostgreSQLStore:
    """Get singleton PostgreSQL store instance"""
    global _postgresql_store
    if _postgresql_store is None:
        _postgresql_store = PostgreSQLStore()
    return _postgresql_store


# Maintain compatibility with old function names
def get_mongodb_store() -> PostgreSQLStore:
    """Compatibility wrapper - redirects to PostgreSQL store"""
    return get_postgresql_store()


def init_mongodb_store(*args, **kwargs) -> PostgreSQLStore:
    """Compatibility wrapper - redirects to PostgreSQL store"""
    return get_postgresql_store()


def close_postgresql_store():
    """Close PostgreSQL store connection"""
    global _postgresql_store
    if _postgresql_store:
        _postgresql_store.close()
        _postgresql_store = None


def close_mongodb_store():
    """Compatibility wrapper - redirects to PostgreSQL close"""
    close_postgresql_store()


# Provide compatibility with old class name
MongoDBStore = PostgreSQLStore

# Don't auto-initialize here to avoid circular import
# Initialize only when called from load_config.py