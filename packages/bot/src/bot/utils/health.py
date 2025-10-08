# src/utils/health.py
"""
Health check module to verify all services before bot startup.
Ensures Discord token, database, and other dependencies are operational.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Tuple
from datetime import datetime

logger = logging.getLogger("HealthCheck")

# Import colorama for colored output
try:
    from colorama import init, Fore, Style

    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False


    class Fore:
        RESET = GREEN = BRIGHT = RED = ""


    class Style:
        RESET_ALL = ""


class ServiceHealthChecker:
    """Checks health status of all required services before bot startup."""

    def __init__(self, config):
        self.config = config

    def check_ai_gateway(self) -> Tuple[bool, str]:
        """
        Statically checks the status of the integrated AI Gateway.
        """
        providers = getattr(self.config, 'ALLOWED_PROVIDERS', set())
        return True, (
            f"AI Gateway: [OK] Integrated\n"
            f"  - Mode: Direct function call\n"
            f"  - Providers Configured: {', '.join(sorted(providers)) or 'None'}"
        )

    async def check_mongodb(self) -> Tuple[bool, str]:
        """
        Check if MongoDB is accessible and operational.
        """
        try:
            connection_string = getattr(self.config, 'MONGODB_CONNECTION_STRING', None)
            if not connection_string:
                return False, "MongoDB: [ERROR] MONGODB_CONNECTION_STRING is not set"

            from bot.storage.database import get_mongodb_store
            store = get_mongodb_store()

            # Run blocking IO in a separate thread to avoid blocking the event loop
            await asyncio.to_thread(store.db.command, "ping")

            collections, user_count, model_count = await asyncio.gather(
                asyncio.to_thread(store.db.list_collection_names),
                asyncio.to_thread(store.db.user_configs.count_documents, {}),
                asyncio.to_thread(store.db.supported_models.count_documents, {})
            )
            return True, (
                f"MongoDB: [OK] Connected\n"
                f"  - Database: {store.database_name}\n"
                f"  - Collections: {len(collections)}\n"
                f"  - Users: {user_count}\n"
                f"  - Models: {model_count}"
            )
        except Exception as e:
            return False, f"MongoDB: [ERROR] Connection Failed: {type(e).__name__}: {str(e)[:100]}"

    async def check_discord_token(self) -> Tuple[bool, str]:
        """
        Check if Discord token is valid by making a request to the Discord API.
        """
        try:
            discord_token = getattr(self.config, 'DISCORD_TOKEN', None)
            if not discord_token:
                return False, "Discord Token: [ERROR] DISCORD_TOKEN is not configured"

            headers = {"Authorization": f"Bot {discord_token}"}
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get("https://discord.com/api/v10/users/@me", headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return True, (
                            f"Discord Token: [OK] Valid\n"
                            f"  - Bot: {data.get('username', 'N/A')}\n"
                            f"  - ID: {data.get('id', 'N/A')}"
                        )
                    elif response.status == 401:
                        return False, "Discord Token: [ERROR] Invalid. Authentication failed."
                    else:
                        error_text = await response.text()
                        return False, f"Discord Token: [ERROR] Status {response.status}: {error_text[:100]}"
        except Exception as e:
            return False, f"Discord Token: [ERROR] Request failed: {type(e).__name__}: {str(e)[:100]}"

    async def check_file_permissions(self) -> Tuple[bool, str]:
        """
        Check if required directories (like 'logs') are writable.
        """
        try:
            from pathlib import Path
            log_dir = Path("logs")
            await asyncio.to_thread(log_dir.mkdir, parents=True, exist_ok=True)
            test_file = log_dir / ".healthcheck"
            # Asynchronous file operations are not standard, so we use to_thread for sync file IO
            await asyncio.to_thread(test_file.touch)
            await asyncio.to_thread(test_file.unlink)
            return True, "File System: [OK] 'logs' directory is writable."
        except Exception as e:
            return False, f"File System: [ERROR] Could not write to 'logs' directory: {e}"

    async def run_all_checks(self) -> Tuple[bool, Dict[str, Tuple[bool, str]]]:
        """Run all health checks."""
        logger.info("Starting health checks...")

        # --- CORE FIX: Separate async and sync checks ---
        # 1. Run all async checks concurrently
        async_checks = {
            "discord": self.check_discord_token(),
            "mongodb": self.check_mongodb(),
            "filesystem": self.check_file_permissions(),
        }
        async_results = await asyncio.gather(*async_checks.values())

        results = dict(zip(async_checks.keys(), async_results))

        # 2. Run sync checks and add them to the results
        results["ai_gateway"] = self.check_ai_gateway()

        all_passed = all(result[0] for result in results.values())
        return all_passed, results

    def _colorize_marker(self, text: str) -> str:
        if not COLORS_AVAILABLE: return text
        markers = {
            '[OK]': f'{Fore.GREEN}{Style.BRIGHT}[OK]{Style.RESET_ALL}',
            '[ERROR]': f'{Fore.RED}{Style.BRIGHT}[ERROR]{Style.RESET_ALL}',
        }
        for marker, colored in markers.items():
            text = text.replace(marker, colored)
        return text

    def print_results(self, results: Dict[str, Tuple[bool, str]], all_passed: bool):
        header = f"{'=' * 20} [HEALTH CHECK] {'=' * 20}"
        print(f"\n{header}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * len(header))

        # Define order for consistent output
        check_order = ["discord", "ai_gateway", "mongodb", "filesystem"]
        for name in check_order:
            if name in results:
                _, message = results[name]
                print(self._colorize_marker(message))

        print("-" * len(header))
        if all_passed:
            print(self._colorize_marker("[OK] All checks passed. Bot is ready to start!"))
        else:
            print(self._colorize_marker("[ERROR] Some checks failed. Please review the errors above."))
        print(f"{'=' * len(header)}\n")


async def perform_startup_checks(config) -> bool:
    """Main function to perform all startup checks."""
    checker = ServiceHealthChecker(config)
    all_passed, results = await checker.run_all_checks()
    checker.print_results(results, all_passed)

    if not all_passed:
        failed = [name for name, (success, _) in results.items() if not success]
        logger.error(f"Health checks failed on: {', '.join(failed)}")

    return all_passed