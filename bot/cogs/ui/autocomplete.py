import discord
import emoji
from discord import app_commands

from core.database import get_session_context
from core.models import SignupConfig
from services.config import get_signup_config


async def emoji_autocomplete(
  interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
  with get_session_context() as session:
    signup_config: SignupConfig = get_signup_config(session)

  # Get all custom emojis the bot can see in this server

  guild = interaction.guild
  if guild is None:
    return []

  emojis = signup_config.gvg_reacts
  print(emojis)
  autocomplete_list = []
  for e in emojis:
    # Splits '<:tank:12345>' into ['', 'tank', '12345>']
    if ":" in e:
      display_name = f":{e.split(':')[1]}:"
    else:
      # Is unicode
      display_name = emoji.demojize(e)

    # Autocomplete feature
    if current.lower() in display_name.lower():
      autocomplete_list.append(
        app_commands.Choice(name=f"{e} ({display_name})", value=e)
      )

  return autocomplete_list[:25]
