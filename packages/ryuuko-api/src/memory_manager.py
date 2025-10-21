# /packages/ryuuko-api/src/memory_manager.py

import logging
from typing import List, Dict, Any, Union, Optional
from datetime import datetime
import pytz

from .database import db_store
from .embedding_service import embedding_service
from .summarization_service import summarization_service

logger = logging.getLogger("RyuukoAPI.MemoryManager")

def get_vietnam_timestamp() -> str:
    """Get current timestamp in Vietnam timezone."""
    vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now = datetime.now(vietnam_tz)
    return now.strftime("%A, %d/%m/%Y %H:%M:%S %Z")

class MemoryManager:
    """
    Hierarchical Memory Manager with 3-level architecture:
    - Level 1: Sliding window (10 most recent conversations)
    - Level 2: RAG retrieval (10 most relevant conversations via vector similarity)
    - Level 3: Contextual summarization (high-level story/context summary)
    """

    def __init__(self, database_store):
        self.db = database_store
        self.embedding_service = embedding_service
        self.summarization_service = summarization_service

        # Configuration
        self.SLIDING_WINDOW_SIZE = 10  # Level 1: Recent messages
        self.RAG_RETRIEVAL_SIZE = 10   # Level 2: Similar messages
        self.SUMMARY_UPDATE_THRESHOLD = 10  # Update summary every N messages

    def add_message(self, user_id: str, role: str, content: Any):
        """
        Add a message to the hierarchical memory system.

        Args:
            user_id: User ID
            role: Message role ('user' or 'assistant')
            content: Message content (text or multimodal)
        """
        try:
            # Extract text from content for embedding
            text_content = self._extract_text_from_content(content)

            if not text_content.strip():
                logger.warning(f"Empty text content for user {user_id}, skipping memory node creation")
                return

            # Generate semantic embedding
            embedding_vector = self.embedding_service.encode(text_content)

            # Store memory node with embedding
            self.db.add_memory_node(
                user_id=user_id,
                role=role,
                text_content=text_content,
                semantic_vector=embedding_vector
            )

            logger.debug(f"Added '{role}' memory node for user_id: {user_id}")

            # Check if we should update the summary
            recent_nodes = self.db.get_recent_memory_nodes(user_id, limit=self.SUMMARY_UPDATE_THRESHOLD)
            if len(recent_nodes) >= self.SUMMARY_UPDATE_THRESHOLD:
                self._update_summary_if_needed(user_id, recent_nodes)

        except Exception as e:
            logger.error(f"Error adding message to hierarchical memory: {e}")
            raise

    def prepare_prompt_history(
        self,
        user_id: str,
        new_messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Prepare conversation history using 3-level hierarchical memory.
        Returns structured payload with single system message containing all context.

        Args:
            user_id: User ID
            new_messages: New messages from current request
            system_prompt: User's custom system prompt/persona

        Returns:
            Structured payload: [system_message, user_message]
        """
        try:
            logger.debug(f"Preparing hierarchical prompt history for user_id: {user_id}")

            # Extract query text from new messages for RAG retrieval
            query_texts = []
            for msg in new_messages:
                text = self._extract_text_from_content(msg.get('content', ''))
                if text.strip():
                    query_texts.append(text)

            # Extract latest user message content
            latest_user_content = new_messages[-1].get('content', '') if new_messages else ''

            # If no valid query text, use minimal context
            if not query_texts:
                logger.debug("No valid query text, using minimal context")
                return self._build_structured_payload(
                    context_summary="",
                    long_term_memories=[],
                    short_term_memories=[],
                    system_prompt=system_prompt,
                    latest_user_content=latest_user_content
                )

            # Generate query embedding for RAG
            query_text = " ".join(query_texts)
            query_vector = self.embedding_service.encode(query_text)

            # === LEVEL 3: Contextual Summary ===
            context_summary = self._get_contextual_summary(user_id)

            # === LEVEL 2: RAG Retrieval (10 most relevant - Long-term) ===
            rag_history = self._get_rag_history(user_id, query_vector)
            long_term_memories = self._format_memories_as_text(rag_history)

            # === LEVEL 1: Sliding Window (10 most recent - Short-term) ===
            recent_history = self._get_sliding_window_history(user_id)
            short_term_memories = self._format_memories_as_text(recent_history)

            logger.debug(
                f"Prepared history - Summary: {bool(context_summary)}, "
                f"Long-term: {len(long_term_memories)}, Short-term: {len(short_term_memories)}"
            )

            # Build structured payload
            return self._build_structured_payload(
                context_summary=context_summary,
                long_term_memories=long_term_memories,
                short_term_memories=short_term_memories,
                system_prompt=system_prompt,
                latest_user_content=latest_user_content
            )

        except Exception as e:
            logger.error(f"Error preparing hierarchical prompt history: {e}")
            # Fallback to minimal context
            latest_user_content = new_messages[-1].get('content', '') if new_messages else ''
            return self._build_structured_payload(
                context_summary="",
                long_term_memories=[],
                short_term_memories=[],
                system_prompt=system_prompt,
                latest_user_content=latest_user_content
            )

    def _format_memories_as_text(self, messages: List[Dict[str, Any]]) -> List[str]:
        """
        Format memory messages as text snippets.

        Args:
            messages: List of message dictionaries

        Returns:
            List of formatted text snippets
        """
        formatted = []
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if isinstance(content, str):
                formatted.append(f"{role.upper()}: {content}")
            else:
                # Handle multimodal content
                text = self._extract_text_from_content(content)
                if text:
                    formatted.append(f"{role.upper()}: {text}")
        return formatted

    def _build_structured_payload(
        self,
        context_summary: str,
        long_term_memories: List[str],
        short_term_memories: List[str],
        system_prompt: Optional[str],
        latest_user_content: Any
    ) -> List[Dict[str, Any]]:
        """
        Build the final structured payload with single system message.

        Args:
            context_summary: Level 3 summary
            long_term_memories: Level 2 RAG memories
            short_term_memories: Level 1 recent memories
            system_prompt: User's persona/meta prompt
            latest_user_content: Latest user message content

        Returns:
            Structured payload [system_message, user_message]
        """
        # Get current Vietnam timestamp
        current_time = get_vietnam_timestamp()

        # Format long-term memories
        long_term_section = '\n'.join(long_term_memories) if long_term_memories else 'Không có.'

        # Format short-term memories
        short_term_section = '\n'.join(short_term_memories) if short_term_memories else 'Không có.'

        # Build system content
        system_content_parts = [
            "[THỜI GIAN HIỆN TẠI]",
            current_time,
            "",
            "[BỐI CẢNH TÓM TẮT]",
            context_summary if context_summary else "Không có.",
            "",
            "[KÝ ỨC DÀI HẠN LIÊN QUAN]",
            long_term_section,
            "",
            "[LỊCH SỬ CHAT GẦN ĐÂY]",
            short_term_section,
            ""
        ]

        # Add meta prompt/persona if provided
        if system_prompt:
            system_content_parts.extend([
                "# === ĐỀ MỤC PERSONA & QUY TẮC ===",
                system_prompt,
                "# === KẾT THÚC ĐỀ MỤC ==="
            ])

        system_content = "\n".join(system_content_parts)

        # Build final payload
        payload = [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": latest_user_content
            }
        ]

        return payload

    def _get_sliding_window_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Level 1: Get sliding window of recent messages.

        Args:
            user_id: User ID

        Returns:
            List of recent message dictionaries
        """
        try:
            recent_nodes = self.db.get_recent_memory_nodes(
                user_id,
                limit=self.SLIDING_WINDOW_SIZE
            )

            # Convert nodes to message format
            messages = []
            for node in recent_nodes:
                messages.append({
                    "role": node.get("role"),
                    "content": node.get("text_content")
                })

            return messages
        except Exception as e:
            logger.error(f"Error getting sliding window history: {e}")
            return []

    def _get_rag_history(
        self,
        user_id: str,
        query_vector: List[float]
    ) -> List[Dict[str, Any]]:
        """
        Level 2: Get RAG-retrieved relevant messages.

        Args:
            user_id: User ID
            query_vector: Query embedding vector

        Returns:
            List of relevant message dictionaries
        """
        try:
            similar_nodes = self.db.search_similar_memory_nodes(
                user_id=user_id,
                query_vector=query_vector,
                limit=self.RAG_RETRIEVAL_SIZE,
                exclude_recent=self.SLIDING_WINDOW_SIZE
            )

            # Convert nodes to message format (sorted by timestamp for coherence)
            messages = []
            for node in sorted(similar_nodes, key=lambda x: x.get('timestamp', '')):
                messages.append({
                    "role": node.get("role"),
                    "content": node.get("text_content")
                })

            return messages
        except Exception as e:
            logger.error(f"Error getting RAG history: {e}")
            return []

    def _get_contextual_summary(self, user_id: str) -> str:
        """
        Level 3: Get contextual summary.

        Args:
            user_id: User ID

        Returns:
            Summary text or empty string
        """
        try:
            summary = self.db.get_memory_summary(user_id)
            return summary or ""
        except Exception as e:
            logger.error(f"Error getting contextual summary: {e}")
            return ""

    def _update_summary_if_needed(
        self,
        user_id: str,
        recent_nodes: List[Dict[str, Any]]
    ):
        """
        Update the contextual summary with recent conversations.

        Args:
            user_id: User ID
            recent_nodes: Recent memory nodes
        """
        try:
            # Convert nodes to message format
            messages = []
            for node in recent_nodes:
                messages.append({
                    "role": node.get("role"),
                    "content": node.get("text_content")
                })

            # Get existing summary
            existing_summary = self.db.get_memory_summary(user_id)

            # Generate updated summary
            new_summary = self.summarization_service.update_summary(
                existing_summary=existing_summary or "",
                new_messages=messages,
                max_messages_for_update=self.SUMMARY_UPDATE_THRESHOLD
            )

            # Save updated summary
            if new_summary:
                self.db.update_memory_summary(user_id, new_summary)
                logger.debug(f"Updated contextual summary for user {user_id}")

        except Exception as e:
            logger.error(f"Error updating summary: {e}")

    def clear_history(self, user_id: str) -> bool:
        """
        Clear all memory (nodes + summary) for a user.
        This will RESET all chatbot memory with this user.

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        try:
            logger.info(f"Clearing all hierarchical memory for user_id: {user_id}")

            # Clear memory nodes (Level 1 & 2)
            nodes_deleted = self.db.clear_memory_nodes(user_id)

            # Clear contextual summary (Level 3)
            summary_deleted = self.db.clear_memory_summary(user_id)

            logger.info(
                f"Cleared memory for user {user_id}: "
                f"nodes={nodes_deleted}, summary={summary_deleted}"
            )

            return True
        except Exception as e:
            logger.error(f"Error clearing memory: {e}")
            return False

    def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get full conversation history (for backward compatibility).
        Returns recent nodes from the new system.

        Args:
            user_id: User ID

        Returns:
            List of message dictionaries
        """
        return self._get_sliding_window_history(user_id)

    def _extract_text_from_content(self, content: Any) -> str:
        """
        Extract text from message content (handles string and multimodal).

        Args:
            content: Message content

        Returns:
            Extracted text string
        """
        return self.embedding_service.extract_text_from_content(content)

# Create a single, shared instance of the MemoryManager
memory_manager = MemoryManager(db_store)
