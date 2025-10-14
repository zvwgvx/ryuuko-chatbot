# /packages/discord-bot/src/utils/embed.py
import discord

async def send_embed(ctx, title: str, description: str, color: discord.Color):
    """Creates and sends a standardized embed message."""
    embed = discord.Embed(title=title, description=description, color=color)
    await ctx.send(embed=embed)
