# /packages/discord-bot/src/utils/queue.py
import asyncio
import logging
from collections import namedtuple

logger = logging.getLogger("DiscordBot.Utils.Queue")

Request = namedtuple('Request', ['message', 'final_user_text'])

class RequestQueue:
    def __init__(self):
        self._queue = asyncio.Queue()
        self._worker_task = None
        self._process_callback = None

    def set_process_callback(self, callback):
        self._process_callback = callback
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("Request queue worker started")

    async def add_request(self, message, final_user_text):
        await self._queue.put(Request(message, final_user_text))
        logger.info(f"Adding request to queue for user {message.author.id}: {final_user_text[:50]}")

    async def _worker(self):
        while True:
            try:
                request = await self._queue.get()
                if self._process_callback:
                    await self._process_callback(request)
                self._queue.task_done()
            except Exception as e:
                logger.exception(f"Error in request queue worker: {e}")

_request_queue_instance = None

def get_request_queue() -> RequestQueue:
    global _request_queue_instance
    if _request_queue_instance is None:
        _request_queue_instance = RequestQueue()
    return _request_queue_instance
