from collections import defaultdict
import re
import discord
from dataclasses import dataclass

from core.database import get_session_context
from core.models import SignupConfig
from services.config import get_signup_config
from services.discord_bus import hydrate_channel, hydrate_message


@dataclass
class RosterMember:
  id: int
  display_name: str
  avatar_url: str
  role_names: list[str]
  is_signed_up: bool = True


@dataclass
class Signup:
  post: discord.Message
  management_channel: discord.TextChannel
  guild: discord.Guild
  roles: list[discord.Role]
  reacts: list[str | discord.Reaction]


async def get_and_hydrate_signup(
  bot: discord.Client, interaction: discord.Interaction | None = None
) -> Signup | None:
  """Basically just a hydration helper."""
  # TODO(@alexandersoen): Probably needs better error handling...

  with get_session_context() as session:
    signup_config: SignupConfig = get_signup_config(session)

  management_channel = await hydrate_channel(bot, signup_config.management_channel)
  signup_post = await hydrate_message(bot, signup_config.selected_post)

  # Error checking on None
  if signup_post is None:
    if interaction:
      await interaction.response.send_message(
        "No post selected. Select post via"
        "More' -> 'Apps' -> 'Signup Analyze: Select Post'",
        ephemeral=True,
      )
    return

  if management_channel is None:
    if interaction:
      await interaction.response.send_message(
        "Management channel required. Use /set_gvg_management_channel.",
        ephemeral=True,
      )
    return

  guild = signup_post.guild
  if guild is None:
    return None

  # Get roles
  roles = []
  for r_id in signup_config.gvg_roles:
    role = guild.get_role(r_id)

    if role:
      roles.append(role)

  # Get reacts
  reacts = []
  for r_str in signup_config.gvg_reacts:
    react = r_str
    custom_emoji_match = re.search(r":(\d+)>", react)
    if custom_emoji_match:
      r_id = int(custom_emoji_match.group(1))

      react = guild.get_emoji(r_id)
      if not react:
        continue

    reacts.append(react)

  return Signup(
    post=signup_post,
    management_channel=management_channel,
    guild=guild,
    reacts=reacts,
    roles=roles,
  )


async def get_react_data(
  guild: discord.Guild, message: discord.Message
) -> dict[str, set[discord.Member]]:
  """Get react data from reacts to user ids."""
  data = defaultdict(set)

  for reaction in message.reactions:
    emoji_str = str(reaction.emoji)

    async for user in reaction.users():
      if user.bot:
        continue

      m = guild.get_member(user.id) or await guild.fetch_member(user.id)
      data[emoji_str].add(m)

  return data
