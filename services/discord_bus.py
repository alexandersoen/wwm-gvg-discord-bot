import discord
from core.models import ChannelConfig, MessageConfig


async def hydrate_channel(
  bot: discord.Client, cfg: ChannelConfig | None
) -> discord.TextChannel | None:
  """Hydrate channel."""
  if not cfg:
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


async def hydrate_message(
  bot: discord.Client, cfg: MessageConfig | None
) -> discord.Message | None:
  if not cfg:
    return None

  channel = await hydrate_channel(bot, cfg.channel_config)
  if not channel:
    return None

  try:
    message = await channel.fetch_message(cfg.message_id)
  except (discord.NotFound, discord.Forbidden):
    return None

  return message
