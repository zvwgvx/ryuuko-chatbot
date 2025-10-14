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
        super().__init__(command_prefix="r", intents=intents, help_command=None)

    async def setup_hook(self) -> None:
        """This is called automatically by discord.py after the bot is logged in."""
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
        """Handles errors that occur when a command is invoked."""
        if isinstance(error, commands.MissingRequiredArgument):
            command = ctx.command
            params = list(command.clean_params.values())
            
            try:
                missing_param_index = next(i for i, p in enumerate(params) if p.name == error.param.name)
            except StopIteration:
                await send_embed(
                    ctx,
                    title="Error: Missing Argument",
                    description=f"Oops! You missed a required argument: `{error.param.name}`.",
                    color=discord.Color.red()
                )
                return

            missing_required_params = [
                param for param in params[missing_param_index:] 
                if param.default is param.empty
            ]
            
            missing_args_str = ", ".join([f"`{p.name}`" for p in missing_required_params])
            
            param_signatures = []
            for param in command.clean_params.values():
                if param.default is not param.empty:
                    param_signatures.append(f'[{param.name}]')
                else:
                    param_signatures.append(f'<{param.name}>')
            
            usage_string = f"{ctx.prefix}{command.name} {' '.join(param_signatures)}"

            description = (
                f"Oops! You're missing {len(missing_required_params)} required argument(s): {missing_args_str}.\n\n"
                f"**Correct Usage:**\n`{usage_string}`"
            )

            await send_embed(
                ctx,
                title="Error: Missing Arguments",
                description=description,
                color=discord.Color.red()
            )
        elif isinstance(error, commands.CommandNotFound):
            invoked_command = ctx.invoked_with
            if not invoked_command:
                return

            all_commands = [cmd.name for cmd in self.commands] + [alias for cmd in self.commands for alias in cmd.aliases]
            matches = difflib.get_close_matches(invoked_command, all_commands, n=3, cutoff=0.6)

            if matches:
                suggestions_str = "\n".join([f"• `{ctx.prefix}{match}`" for match in matches])
                description = f"Command `{invoked_command}` not found. Did you mean one of these?\n{suggestions_str}"
                await send_embed(
                    ctx,
                    title="Command Not Found",
                    description=description,
                    color=discord.Color.orange()
                )
        else:
            logger.error(f"An unhandled error occurred in command '{ctx.command}':", exc_info=error)
            await send_embed(
                ctx,
                title="Error: Command Execution Failed",
                description="An unexpected error occurred while running this command. The incident has been logged.",
                color=discord.Color.red()
            )

    async def run_client(self):
        if not config.DISCORD_TOKEN:
            logger.critical("DISCORD_TOKEN is not set. The client cannot start.")
            return
        if not config.CORE_API_URL or not config.CORE_API_KEY:
            logger.critical("CORE_API_URL or CORE_API_KEY is not set. The client cannot connect to the Core Service.")
            return
        
        async with self:
            logger.info("[START] Starting Discord client...")
            await self.start(config.DISCORD_TOKEN)
