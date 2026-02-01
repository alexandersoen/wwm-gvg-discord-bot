from collections import defaultdict
import time
import discord
from discord import app_commands
from discord.ext import commands
from tabulate import tabulate

from bot.cogs.ui.autocomplete import emoji_autocomplete
from bot.cogs.ui.embeds import forward_as_embed
from core.database import get_session_context
from core.models import ChannelConfig, MessageConfig, SignupConfig
from services.config import get_signup_config, update_signup_config
from services.discord_bus import hydrate_channel, hydrate_message


ROLE_NAME_STR_SIZE = 10


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


async def get_overview_table_str(
  guild: discord.Guild, members: set[discord.Member], gvg_role_ids: list[int]
) -> str:
  """A overview table of signups (each role highlighted)."""
  role_objects = []
  headers = ["User"]

  for r_id in gvg_role_ids:
    role = guild.get_role(r_id)
    name = role.name if role else "???"
    role_objects.append(role)
    headers.append(name[:ROLE_NAME_STR_SIZE].upper())

  table_data = []

  def role_weights(member: discord.Member):
    m_roles = {r.id for r in member.roles}
    return tuple(r_id not in m_roles for r_id in gvg_role_ids)

  sorted_members = sorted(
    list(members), key=lambda m: (role_weights(m), m.display_name.lower())
  )
  for member in sorted_members:
    row = [member.display_name[:15]]

    member_role_ids = [r.id for r in member.roles]
    for r_id in gvg_role_ids:
      row.append("✅" if r_id in member_role_ids else " ")

    table_data.append(row)

  table_str = tabulate(table_data, headers=headers, tablefmt="simple")
  role_mentions = " ".join([f"<@&{r_id}>" for r_id in gvg_role_ids])
  return f"### GvG Roster Overview\n```\n{table_str}\n```\n**Roles:** {role_mentions}"


async def get_summary_table_str(
  guild: discord.Guild, members: set[discord.Member], gvg_role_ids: list[int]
) -> str:
  """Summary table of counts."""

  # Prepare Role Metadata
  role_names = []
  for r_id in gvg_role_ids:
    r = guild.get_role(r_id)
    role_names.append(r.name[:ROLE_NAME_STR_SIZE].upper() if r else "???")

  # total_counts: Total people with the role
  # unique_counts: People who have ONLY this role (from the gvg_role_ids list)
  total_counts = [0] * len(gvg_role_ids)
  unique_counts = [0] * len(gvg_role_ids)

  for member in members:
    # Get intersection of member roles and our target roles
    m_role_ids = [r.id for r in member.roles if r.id in gvg_role_ids]

    for i, r_id in enumerate(gvg_role_ids):
      if r_id in m_role_ids:
        total_counts[i] += 1
        # If this is the ONLY target role they have, it's a unique count
        if len(m_role_ids) == 1:
          unique_counts[i] += 1

  # Format Data for Tabulate
  summary_data = [["TOTAL"] + total_counts, ["UNIQUE"] + unique_counts]
  headers = ["Type"] + role_names

  table_str = tabulate(summary_data, headers=headers, tablefmt="simple")

  return f"### 📊 Role Distribution Summary\n```\n{table_str}\n```"


async def get_role_list_str(
  members: set[discord.Member], role_id: int, gvg_role_ids: list[int]
) -> list[str]:
  """Get mention strings by filtered role."""
  member_str_list = []
  for member in members:
    m_role_ids = [r.id for r in member.roles if r.id in gvg_role_ids]

    if role_id not in m_role_ids:
      continue

    m_str = member.mention
    other_gvg_roles = [r_id for r_id in m_role_ids if r_id != role_id]
    if other_gvg_roles:
      other_str = f" (other GvG roles: {' '.join([f'<@&{r_id}>' for r_id in other_gvg_roles])})"
      m_str = m_str + other_str

    member_str_list.append(m_str)

  return member_str_list


class GvGSignup(commands.Cog):
  TIME_TO_STALE = 300

  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot

    # Post Selector

    post_select_ctx_menu = app_commands.ContextMenu(
      name="Signup Analyze: Select Post",
      callback=self.select_post_cb,
    )
    self.bot.tree.add_command(post_select_ctx_menu)

    self._last_fetch_time = 0
    self._last_snapshot: dict[str, set[discord.Member]] = {}

  async def get_cached_react_data(
    self, guild: discord.Guild, message: discord.Message
  ) -> dict[str, set[discord.Member]]:
    """Quick caching of the react data."""
    if time.time() - self._last_fetch_time < self.TIME_TO_STALE:
      return self._last_snapshot

    data = await get_react_data(guild, message)

    self._last_fetch_time = time.time()
    self._last_snapshot = data
    return data

  async def get_valid_signup_info(
    self, interaction: discord.Interaction
  ) -> tuple[discord.Message, discord.TextChannel, SignupConfig] | None:
    """Basically just a hydration helper."""
    with get_session_context() as session:
      signup_config: SignupConfig = get_signup_config(session)

    management_channel = await hydrate_channel(
      self.bot, signup_config.management_channel
    )
    signup_post = await hydrate_message(self.bot, signup_config.selected_post)

    # Error checking on None
    if signup_post is None:
      await interaction.response.send_message(
        "No post selected. Select post via"
        "More' -> 'Apps' -> 'Signup Analyze: Select Post'",
        ephemeral=True,
      )
      return

    if management_channel is None:
      await interaction.response.send_message(
        "Management channel required. Use /set_gvg_management_channel.",
        ephemeral=True,
      )
      return

    return (signup_post, management_channel, signup_config)

  async def select_post_cb(
    self, interaction: discord.Interaction, message: discord.Message
  ) -> None:
    """Callback for selecting post via context menu."""

    # Construct message config
    guild_id = message.guild.id if message.guild else None
    c_config = ChannelConfig(
      channel_id=message.channel.id,
      guild_id=guild_id,
    )
    m_config = MessageConfig(
      message_id=message.id, channel_config=c_config, content=message.content
    )

    # Update DB
    with get_session_context() as session:
      signup_config: SignupConfig = get_signup_config(session)

    signup_config = SignupConfig(
      management_channel=signup_config.management_channel,
      gvg_roles=signup_config.gvg_roles,
      gvg_reacts=signup_config.gvg_reacts,
      selected_post=m_config,
    )
    with get_session_context() as session:
      signup_config = update_signup_config(session, signup_config)

    # Extra bot logging
    if guild_id is None:
      await interaction.followup.send("NOTE: No guild id detected.", ephemeral=True)

    management_channel = await hydrate_channel(
      self.bot, signup_config.management_channel
    )
    forward_embed = await forward_as_embed(
      source_msg=message,
      footer_content="Post selected for GvG signup.",
    )
    if management_channel:
      await management_channel.send(embed=forward_embed)
    else:
      await interaction.response.send_message(embed=forward_embed, ephemeral=True)

  @app_commands.command(
    name="signup_summary",
    description="Summary of signups.",
  )
  @app_commands.describe(
    emoji_choice="Filter signup by emoji (preview may look different than actual emoji)."
  )
  @app_commands.autocomplete(emoji_choice=emoji_autocomplete)
  async def signup_summary(
    self, interaction: discord.Interaction, emoji_choice: str | None = None
  ):
    """Print out signup summary."""
    await interaction.response.defer(ephemeral=True, thinking=False)

    signup_info = await self.get_valid_signup_info(interaction)
    if not signup_info:
      return

    signup_post, management_channel, signup_config = signup_info
    guild = signup_post.guild
    assert guild

    data = await self.get_cached_react_data(guild, signup_post)

    if emoji_choice is None:
      filtered_members = set().union(*data.values())
    else:
      filtered_members = data[emoji_choice]

    header_str = f"## Signup Summary for {emoji_choice}"
    summary_str = await get_summary_table_str(
      guild, filtered_members, signup_config.gvg_roles
    )
    overview_str = await get_overview_table_str(
      guild, filtered_members, signup_config.gvg_roles
    )

    output_str = "\n".join([header_str, summary_str, overview_str])

    no_pings = discord.AllowedMentions(users=False, roles=False, everyone=False)

    await management_channel.send(output_str, allowed_mentions=no_pings)
    await interaction.delete_original_response()

  @app_commands.command(
    name="signup_by_roles",
    description="Signed up member by roles (and emoji).",
  )
  @app_commands.describe(target_role="The role to check.")
  @app_commands.describe(
    emoji_choice="Filter signup by emoji (preview may look different than actual emoji)."
  )
  @app_commands.autocomplete(emoji_choice=emoji_autocomplete)
  async def signup_by_roles(
    self,
    interaction: discord.Interaction,
    target_role: discord.Role,
    emoji_choice: str | None = None,
  ) -> None:
    """Query member who have signed up by their roles."""
    await interaction.response.defer(ephemeral=True, thinking=False)

    signup_info = await self.get_valid_signup_info(interaction)
    if not signup_info:
      return

    signup_post, management_channel, signup_config = signup_info
    guild = signup_post.guild
    assert guild

    data = await self.get_cached_react_data(guild, signup_post)
    if emoji_choice is None:
      filtered_members = set().union(*data.values())
    else:
      filtered_members = data[emoji_choice]

    role_list_str = await get_role_list_str(
      filtered_members, target_role.id, signup_config.gvg_roles
    )

    no_pings = discord.AllowedMentions(users=False, roles=False, everyone=False)

    setting_str = f"role {target_role.mention}"
    if emoji_choice:
      setting_str = setting_str + f" and react {emoji_choice}"

    if not role_list_str:
      await management_channel.send(
        f"No one with {setting_str} in signup.", allowed_mentions=no_pings
      )
      return

    query_count = len(role_list_str)
    header_str = f"### Found {query_count} members with {setting_str}: "
    res_str = "\n".join(role_list_str)
    output_str = "\n".join([header_str, res_str])

    await management_channel.send(output_str, allowed_mentions=no_pings)
    await interaction.delete_original_response()


async def setup(bot: commands.Bot):
  await bot.add_cog(GvGSignup(bot))
