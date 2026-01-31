import discord
from core.models import ChannelConfig


async def hydrate_channel(
  bot: discord.Client, cfg: ChannelConfig | None
) -> discord.TextChannel | None:
  """Hydrate channel."""
  if not cfg or not cfg.channel_id:
    return None

  # Check cache first
  channel = bot.get_channel(cfg.channel_id)
  if not channel:
    try:
      channel = await bot.fetch_channel(cfg.channel_id)
    except (discord.NotFound, discord.Forbidden):
      return None

  # Only accept text channel
  if isinstance(channel, discord.TextChannel):
    return channel

  return None
