# /packages/discord-bot/src/main.py
import logging
import discord
import difflib
from discord.ext import commands

from . import config
from .utils.queue import get_request_queue
from .utils.embed import send_embed
from .commands import admin, user, basic
from .events import messages

logger = logging.getLogger("DiscordBot.Main")

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix=",", intents=intents, help_command=None)

    async def setup_hook(self) -> None:
        logger.info("[INIT] Initializing client modules inside setup_hook...")
        dependencies = {"request_queue": get_request_queue()}
        admin.setup_admin_commands(self, dependencies)
        user.setup_user_commands(self, dependencies)
        basic.setup_basic_commands(self, dependencies)
        messages.setup_message_events(self, dependencies)
        logger.info("[OK] All client modules initialized.")

    async def on_ready(self):
        logger.info(f"[OK] Discord client is ready: {self.user} (id={self.user.id})")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CheckFailure):
            await send_embed(ctx, title="Permission Denied", description="You do not have the necessary permissions to use this command.", color=discord.Color.red())
            return

        if isinstance(error, commands.MissingRequiredArgument):
            command = ctx.command
            params = list(command.clean_params.values())
            try:
                missing_param_index = next(i for i, p in enumerate(params) if p.name == error.param.name)
            except StopIteration:
                await send_embed(ctx, title="Error: Missing Argument", description=f"Oops! You missed a required argument: `{error.param.name}`.", color=discord.Color.red()); return
            missing_required_params = [p for p in params[missing_param_index:] if p.default is p.empty]
            missing_args_str = ", ".join([f"`{p.name}`" for p in missing_required_params])
            param_signatures = [f'<{p.name}>' if p.default is p.empty else f'[{p.name}]' for p in command.clean_params.values()]
            usage_string = f"{ctx.prefix}{command.name} {' '.join(param_signatures)}"
            description = f"Oops! You're missing {len(missing_required_params)} required argument(s): {missing_args_str}.\n\n**Correct Usage:**\n`{usage_string}`"
            await send_embed(ctx, title="Error: Missing Arguments", description=description, color=discord.Color.red())
        
        elif isinstance(error, commands.CommandNotFound):
            invoked_command = ctx.invoked_with
            if not invoked_command: return

            # --- DIAGNOSTIC LOGGING BLOCK ---
            logger.info("--- [DIAGNOSTIC] CommandNotFound Error ---")
            logger.info(f"[DIAGNOSTIC] Invoked command: '{invoked_command}'")
            
            all_command_names = sorted([cmd.name for cmd in self.commands if not cmd.hidden])
            logger.info(f"[DIAGNOSTIC] All available commands: {all_command_names}")

            # 1. Substring matches
            substring_matches = {name for name in all_command_names if invoked_command in name}
            logger.info(f"[DIAGNOSTIC] Substring matches found: {substring_matches}")

            # 2. Close matches (for typos)
            close_matches = set(difflib.get_close_matches(invoked_command, all_command_names, n=5, cutoff=0.6))
            logger.info(f"[DIAGNOSTIC] Close (typo) matches found: {close_matches}")

            # 3. Combine results
            matches = sorted(list(substring_matches | close_matches))
            logger.info(f"[DIAGNOSTIC] Final combined matches: {matches}")
            # --- END DIAGNOSTIC LOGGING BLOCK ---
            
            if matches:
                suggestions_str = "\n".join([f"• `{ctx.prefix}{match}`" for match in matches])
                description = f"Command `{invoked_command}` not found. Did you mean one of these?\n{suggestions_str}"
                await send_embed(ctx, title="Command Not Found", description=description, color=discord.Color.orange())

        else:
            logger.error(f"An unhandled error occurred in command '{ctx.command}':", exc_info=error)

    async def run_client(self):
        if not config.DISCORD_TOKEN: logger.critical("DISCORD_TOKEN is not set."); return
        if not config.CORE_API_URL or not config.CORE_API_KEY: logger.critical("CORE_API_URL or CORE_API_KEY is not set."); return
        
        async with self:
            logger.info("[START] Starting Discord client...")
            await self.start(config.DISCORD_TOKEN)
