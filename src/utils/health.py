# src/utils/health.py
"""
Health check module to verify all services before bot startup.
Ensures API server, database, and other dependencies are operational.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Tuple, List
from datetime import datetime
import sys

logger = logging.getLogger("HealthCheck")

# Import colorama for colored output
try:
    from colorama import Fore, Style, Back

    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False


    # Fallback
    class Fore:
        BLACK = RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""


    class Style:
        DIM = NORMAL = BRIGHT = RESET_ALL = ""


    class Back:
        BLACK = RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""


class ServiceHealthChecker:
    """Checks health status of all required services before bot startup."""

    def __init__(self, config):
        """
        Initialize health checker with configuration.

        Args:
            config: Configuration module containing service endpoints and credentials
        """
        self.config = config
        self.results = {}

    async def check_api_server(self) -> Tuple[bool, str]:
        """
        Check if API server is accessible and API key is valid.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get API server URL and key from config
            api_server = getattr(self.config, 'API_SERVER', None)
            api_key = getattr(self.config, 'API_KEY', None)

            if not api_server:
                return False, "API Server: [ERROR] API_SERVER not configured in config"

            if not api_key:
                return False, "API Server: [ERROR] API_KEY not configured in config"

            # Build health endpoint URL
            if api_server.endswith('/proxy'):
                base_url = api_server.rsplit('/proxy', 1)[0]
            else:
                base_url = api_server.rstrip('/')

            health_endpoint = f"{base_url}/health"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(health_endpoint, headers=headers) as response:
                    data = await response.json()

                    if response.status == 200 and data.get("authenticated"):
                        providers = data.get("providers_configured", {})
                        active_providers = [p for p, status in providers.items() if status]

                        return True, (
                            f"API Server: [OK] Online\n"
                            f"  - Endpoint: {health_endpoint}\n"
                            f"  - Authentication: Valid\n"
                            f"  - Active Providers: {', '.join(active_providers) if active_providers else 'None'}"
                        )
                    elif response.status == 401:
                        return False, (
                            f"API Server: [ERROR] Authentication Failed\n"
                            f"  - Invalid API key\n"
                            f"  - Check API_KEY in config"
                        )
                    else:
                        return False, (
                            f"API Server: [WARN] Unexpected Response\n"
                            f"  - Status: {response.status}\n"
                            f"  - Response: {data}"
                        )

        except aiohttp.ClientConnectorError:
            return False, (
                f"API Server: [ERROR] Connection Failed\n"
                f"  - Cannot connect to {health_endpoint}\n"
                f"  - Server may be offline or URL is incorrect"
            )
        except asyncio.TimeoutError:
            return False, (
                f"API Server: [ERROR] Timeout\n"
                f"  - Server not responding within 10 seconds"
            )
        except Exception as e:
            return False, (
                f"API Server: [ERROR] Error\n"
                f"  - {type(e).__name__}: {str(e)}"
            )

    async def check_mongodb(self) -> Tuple[bool, str]:
        """
        Check if MongoDB is accessible and operational.

        Returns:
            Tuple of (success, message)
        """
        use_mongodb = getattr(self.config, 'USE_MONGODB', False)

        if not use_mongodb:
            return True, "MongoDB: [SKIP] Skipped (File storage mode)"

        try:
            connection_string = getattr(self.config, 'MONGODB_CONNECTION_STRING', None)

            if not connection_string:
                return False, (
                    "MongoDB: [ERROR] Configuration Missing\n"
                    f"  - MONGODB_CONNECTION_STRING not set in config"
                )

            from src.storage.database import get_mongodb_store, init_mongodb_store

            try:
                store = get_mongodb_store()
            except RuntimeError:
                db_name = getattr(self.config, 'MONGO_DB_NAME', 'polydevsdb')
                store = init_mongodb_store(connection_string, db_name)

            test_result = store.db.command("ping")

            if test_result.get("ok") == 1:
                collections = store.db.list_collection_names()
                user_count = store.db.user_configs.count_documents({})
                model_count = store.db.supported_models.count_documents({})

                return True, (
                    f"MongoDB: [OK] Connected\n"
                    f"  - Database: {store.database_name}\n"
                    f"  - Collections: {len(collections)}\n"
                    f"  - Users: {user_count}\n"
                    f"  - Models: {model_count}"
                )
            else:
                return False, "MongoDB: [ERROR] Ping failed"

        except ImportError:
            return False, (
                "MongoDB: [ERROR] pymongo not installed\n"
                f"  - Run: pip install pymongo"
            )
        except Exception as e:
            return False, (
                f"MongoDB: [ERROR] Connection Failed\n"
                f"  - {type(e).__name__}: {str(e)[:100]}\n"
                f"  - Check MONGODB_CONNECTION_STRING"
            )

    async def check_discord_token(self) -> Tuple[bool, str]:
        """
        Check if Discord token is valid by testing Discord API.

        Returns:
            Tuple of (success, message)
        """
        try:
            discord_token = getattr(self.config, 'DISCORD_TOKEN', None)

            if not discord_token:
                return False, (
                    "Discord Token: [ERROR] Not Configured\n"
                    f"  - DISCORD_TOKEN not set in config or environment"
                )

            headers = {
                "Authorization": f"Bot {discord_token}",
                "Content-Type": "application/json"
            }

            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                        "https://discord.com/api/v10/users/@me",
                        headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        bot_username = data.get('username', 'Unknown')
                        bot_id = data.get('id', 'Unknown')
                        return True, (
                            f"Discord Token: [OK] Valid\n"
                            f"  - Bot: {bot_username}\n"
                            f"  - ID: {bot_id}"
                        )
                    elif response.status == 401:
                        return False, (
                            "Discord Token: [ERROR] Invalid\n"
                            f"  - Token authentication failed\n"
                            f"  - Check DISCORD_TOKEN in config"
                        )
                    else:
                        error_data = await response.text()
                        return False, (
                            f"Discord Token: [ERROR] Error\n"
                            f"  - Status {response.status}\n"
                            f"  - {error_data[:100]}"
                        )

        except Exception as e:
            return False, (
                f"Discord Token: [ERROR] Error\n"
                f"  - {type(e).__name__}: {str(e)[:100]}"
            )

    async def check_file_permissions(self) -> Tuple[bool, str]:
        """
        Check if required directories are writable.

        Returns:
            Tuple of (success, message)
        """
        try:
            import os
            from pathlib import Path

            issues = []
            checked_paths = []

            log_dir = Path("logs")
            if not log_dir.exists():
                try:
                    log_dir.mkdir(parents=True, exist_ok=True)
                    checked_paths.append("logs/ (created)")
                except Exception as e:
                    issues.append(f"logs/ cannot create: {e}")
            elif not os.access(log_dir, os.W_OK):
                issues.append(f"logs/ not writable")
            else:
                checked_paths.append("logs/ [DONE]")

            use_mongodb = getattr(self.config, 'USE_MONGODB', False)
            if not use_mongodb:
                data_dir = Path("data")
                if not data_dir.exists():
                    try:
                        data_dir.mkdir(parents=True, exist_ok=True)
                        checked_paths.append("data/ (created)")
                    except Exception as e:
                        issues.append(f"data/ cannot create: {e}")
                elif not os.access(data_dir, os.W_OK):
                    issues.append(f"data/ not writable")
                else:
                    checked_paths.append("data/ [DONE]")

            if issues:
                return False, (
                        f"File System: [ERROR] Issues found\n"
                        f"  - " + "\n  - ".join(issues)
                )
            else:
                return True, (
                        f"File System: [OK] Ready\n"
                        f"  - " + "\n  - ".join(checked_paths)
                )

        except Exception as e:
            return False, f"File System: [ERROR] Error - {str(e)}"

    async def run_all_checks(self) -> Tuple[bool, Dict[str, Tuple[bool, str]]]:
        """Run all health checks in parallel."""
        logger.info("Starting health checks...")

        checks = {
            "discord": self.check_discord_token(),
            "api_server": self.check_api_server(),
            "mongodb": self.check_mongodb(),
            "filesystem": self.check_file_permissions()
        }

        results = {}
        for name, coro in checks.items():
            success, message = await coro
            results[name] = (success, message)

        all_passed = all(result[0] for result in results.values())
        return all_passed, results

    def colorize_marker(self, text: str) -> str:
        """Apply colors to markers in text"""
        if not COLORS_AVAILABLE:
            return text

        # Marker color mapping
        markers = {
            '[OK]': Fore.GREEN + Style.BRIGHT + '[OK]' + Style.RESET_ALL,
            '[ERROR]': Fore.RED + Style.BRIGHT + '[ERROR]' + Style.RESET_ALL,
            '[WARN]': Fore.YELLOW + '[WARN]' + Style.RESET_ALL,
            '[SKIP]': Fore.CYAN + Style.DIM + '[SKIP]' + Style.RESET_ALL,
            '[DONE]': Fore.GREEN + '[DONE]' + Style.RESET_ALL,
            '[SUCCESS]': Fore.GREEN + Style.BRIGHT + '[SUCCESS]' + Style.RESET_ALL,
            '[FAILURE]': Fore.RED + Style.BRIGHT + '[FAILURE]' + Style.RESET_ALL,
            '[TIME]': Fore.BLUE + '[TIME]' + Style.RESET_ALL,
            '[HEALTH CHECK]': Fore.CYAN + Style.BRIGHT + '[HEALTH CHECK]' + Style.RESET_ALL,
        }

        for marker, colored in markers.items():
            text = text.replace(marker, colored)

        return text

    def print_results(self, results: Dict[str, Tuple[bool, str]], all_passed: bool):
        """Print formatted health check results with colors."""
        if COLORS_AVAILABLE:
            print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
            print(self.colorize_marker("[HEALTH CHECK] System Status Report"))
            print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
            print(self.colorize_marker(f"[TIME] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
            print(f"{Fore.CYAN}{'-' * 60}{Style.RESET_ALL}")
        else:
            print("\n" + "=" * 60)
            print("[HEALTH CHECK] System Status Report")
            print("=" * 60)
            print(f"[TIME] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 60)

        # Print each result with colors
        for check_name, (success, message) in results.items():
            colored_message = self.colorize_marker(message)
            print(f"\n{colored_message}")

        # Print final result
        if COLORS_AVAILABLE:
            print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
            if all_passed:
                print(self.colorize_marker("[SUCCESS] ALL CHECKS PASSED - Bot ready to start!"))
            else:
                print(self.colorize_marker("[FAILURE] SOME CHECKS FAILED - Please fix issues before starting bot"))
            print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
        else:
            print("\n" + "=" * 60)
            if all_passed:
                print("[SUCCESS] ALL CHECKS PASSED - Bot ready to start!")
            else:
                print("[FAILURE] SOME CHECKS FAILED - Please fix issues before starting bot")
            print("=" * 60 + "\n")


async def perform_startup_checks(config) -> bool:
    """Main function to perform all startup checks."""
    checker = ServiceHealthChecker(config)
    all_passed, results = await checker.run_all_checks()
    checker.print_results(results, all_passed)

    if not all_passed:
        failed = [name for name, (success, _) in results.items() if not success]
        logger.error(f"Health checks failed: {', '.join(failed)}")

    return all_passed