# /packages/discord-bot/src/utils/embed.py
import discord
from discord.ext import commands
import logging

logger = logging.getLogger("DiscordBot.Utils.Embed")

async def send_embed(ctx_or_channel, title: str, description: str, color: discord.Color, reference: discord.Message = None):
    """Creates and sends a standardized embed message, safely handling references."""
    embed = discord.Embed(title=title, description=description, color=color)
    
    if isinstance(ctx_or_channel, commands.Context):
        target = ctx_or_channel
    else:
        target = ctx_or_channel

    try:
        # The library is smart enough to handle references correctly.
        # If the reference message is deleted, it will raise an HTTPException.
        if reference:
            await target.send(embed=embed, reference=reference, mention_author=False)
        else:
            await target.send(embed=embed)
    except discord.HTTPException as e:
        # This can happen if the reference message is deleted before the bot can reply.
        # In that case, we fall back to sending without the reference.
        logger.warning(f"Failed to send embed with reference (Error: {e}), falling back to sending without reference.")
        await target.send(embed=embed)
