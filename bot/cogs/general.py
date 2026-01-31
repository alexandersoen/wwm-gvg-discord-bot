import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.ui.views import ReactionSetupView, RolePersistenceView
from core.database import get_session_context
from core.models import ChannelConfig, SignupConfig
from services.config import get_signup_config, update_signup_config
from services.discord_bus import hydrate_channel


async def get_gvg_status_str(signup_config: SignupConfig) -> str:
  # Report
  lines = ["## 🛡️ GvG Configuration Summary"]

  # Format Admin Channel
  if signup_config.admin_channel:
    lines.append(f"**Admin Channel:** <#{signup_config.admin_channel.channel_id}>")
  else:
    lines.append("**Admin Channel:** ⚠️ Not set")

  # Format Tracking Post
  if signup_config.selected_post:
    # Create a jump link to the tracked message
    p = signup_config.selected_post
    jump_url = f"https://discord.com/channels/{p.channel_config.guild_id}/{p.channel_config.channel_id}/{p.message_id}"
    lines.append(f"**Tracking Post:** [Jump to Message]({jump_url})")
  else:
    lines.append("**Tracking Post:** ⚠️ None")

  # Format Emojis & Roles
  emoji_str = " ".join(signup_config.gvg_reacts) if signup_config.gvg_reacts else "None"
  lines.append(f"**Tracked Emojis:** {emoji_str}")

  role_str = (
    " ".join([f"<@&{rid}>" for rid in signup_config.gvg_roles])
    if signup_config.gvg_roles
    else "None"
  )
  lines.append(f"**GvG Roles:** {role_str}")

  summary_text = "\n".join(lines)
  return summary_text


class General(commands.Cog):
  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot

  @app_commands.command(
    name="set_gvg_admin_channel", description="Where to post gvg bot messages."
  )
  @app_commands.describe(admin_channel="Set the GvG admin channel.")
  async def set_gvg_admin_channel(
    self, interaction: discord.Interaction, admin_channel: discord.TextChannel
  ):
    c_config = ChannelConfig(
      channel_id=admin_channel.id, guild_id=admin_channel.guild.id
    )

    # Update DB
    with get_session_context() as session:
      signup_config: SignupConfig = get_signup_config(session)
      signup_config = SignupConfig(
        selected_post=signup_config.selected_post,
        gvg_roles=signup_config.gvg_roles,
        gvg_reacts=signup_config.gvg_reacts,
        admin_channel=c_config,
      )

      signup_config = update_signup_config(session, signup_config)

    await interaction.response.send_message(
      f"Admin channel set to: {admin_channel}", ephemeral=True
    )

  @app_commands.command(
    name="set_gvg_roles", description="Open up menu to select GvG roles."
  )
  async def manage_roles(self, interaction: discord.Interaction):
    if interaction.guild is None:
      await interaction.response.send_message(
        "Command made in unknown guild. Exiting", ephemeral=True
      )
      return

    # Get current info
    with get_session_context() as session:
      signup_config: SignupConfig = get_signup_config(session)

    # Pass the current set and the guild roles to the view
    view = RolePersistenceView(signup_config.gvg_roles, interaction.guild.roles)
    await interaction.response.send_message(
      "Select GvG class roles:",
      view=view,
      ephemeral=True,
    )

    await view.wait()
    if not view.confirmed:
      await interaction.followup.send("Role selection timeout. Exiting", ephemeral=True)
      return

    # Update DB (repull incase changes)
    with get_session_context() as session:
      signup_config: SignupConfig = get_signup_config(session)
      signup_config = SignupConfig(
        admin_channel=signup_config.admin_channel,
        selected_post=signup_config.selected_post,
        gvg_reacts=signup_config.gvg_reacts,
        gvg_roles=view.role_ids,
      )

      signup_config = update_signup_config(session, signup_config)

    # Confirm update to user
    admin_channel = await hydrate_channel(self.bot, signup_config.admin_channel)
    if admin_channel:
      await admin_channel.send(
        f"Updated! Tracking {len(view.role_ids)} roles.",
      )
    else:
      await interaction.followup.send(
        f"Updated! Tracking {len(view.role_ids)} roles.", ephemeral=True
      )

  @app_commands.command(name="set_gvg_reactions")
  async def set_gvg_reactions(self, interaction: discord.Interaction) -> None:
    """Set GvG reactions."""
    with get_session_context() as session:
      signup_config: SignupConfig = get_signup_config(session)

    admin_channel = await hydrate_channel(self.bot, signup_config.admin_channel)
    if admin_channel is None:
      await interaction.response.send_message(
        "Admin channel required to be specified to add GvG reactions. Use /set_gvg_admin_channel.",
        ephemeral=True,
      )
      return

    if interaction.channel != admin_channel:
      await interaction.response.send_message(
        f"GvG reactions setup must be done in admin channel: {admin_channel.name}.",
        ephemeral=True,
      )
      return

    canvas = await admin_channel.send(
      f"**Setup Canvas for {interaction.user.display_name}**\n"
      "Please add all GvG emojis you want to use as reactions to *this* message."
    )

    view = ReactionSetupView(canvas)
    await interaction.response.send_message(
      "Use the message above to select your emojis. Click the button below when done.",
      view=view,
      ephemeral=True,
    )

    await view.wait()
    reactions = view.result

    if not reactions:
      await interaction.followup.send(
        "No reactions selected. Exiting.",
        ephemeral=True,
      )

    # Update DB
    with get_session_context() as session:
      signup_config: SignupConfig = get_signup_config(session)
      signup_config = SignupConfig(
        admin_channel=signup_config.admin_channel,
        selected_post=signup_config.selected_post,
        gvg_roles=signup_config.gvg_roles,
        gvg_reacts=list(reactions),
      )
      signup_config = update_signup_config(session, signup_config)

    # Confirm update to user
    await admin_channel.send(f"Updated! GvG reactions set: {' '.join(reactions)}.")

  @app_commands.command(
    name="peak_gvg_config", description="Peak current GvG configuration."
  )
  async def peak_gvg_config(self, interaction: discord.Interaction):
    """Peak the config in any channel."""
    # Get the config from DB
    with get_session_context() as session:
      signup_config: SignupConfig = get_signup_config(session)

    summary_text = await get_gvg_status_str(signup_config)
    await interaction.response.send_message(summary_text, ephemeral=True)

  @app_commands.command(
    name="post_gvg_config",
    description="Post current GvG configuration to admin channel.",
  )
  async def post_gvg_config(self, interaction: discord.Interaction):
    """Post the config in the admin channel."""
    # Get the config from DB
    with get_session_context() as session:
      signup_config: SignupConfig = get_signup_config(session)

    admin_channel = await hydrate_channel(self.bot, signup_config.admin_channel)
    if not admin_channel:
      await interaction.response.send_message(
        "Admin channel required to be specified to add GvG reactions. Use /set_gvg_admin_channel.",
        ephemeral=True,
      )
      return

    summary_text = await get_gvg_status_str(signup_config)
    await interaction.response.send_message(summary_text, ephemeral=True)
    await admin_channel.send(summary_text)


async def setup(bot: commands.Bot):
  await bot.add_cog(General(bot))
