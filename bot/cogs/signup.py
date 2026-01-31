import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.ui.embeds import forward_as_embed
from core.database import get_session_context
from core.models import ChannelConfig, MessageConfig, SignupConfig
from services.config import get_signup_config, update_signup_config
from services.discord_bus import hydrate_channel


class GvGSignup(commands.Cog):
  SIGN_UP_REACT = "❤️"

  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot

    # Post Selector
    post_select_ctx_menu = app_commands.ContextMenu(
      name="Signup Analyze: Select Post",
      callback=self.select_post_cb,
    )
    self.bot.tree.add_command(post_select_ctx_menu)

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
      admin_channel=signup_config.admin_channel,
      gvg_roles=signup_config.gvg_roles,
      gvg_reacts=signup_config.gvg_reacts,
      selected_post=m_config,
    )
    with get_session_context() as session:
      signup_config = update_signup_config(session, signup_config)

    # Extra bot logging
    if guild_id is None:
      await interaction.followup.send("NOTE: No guild id detected.", ephemeral=True)

    admin_channel = await hydrate_channel(self.bot, signup_config.admin_channel)
    forward_embed = await forward_as_embed(
      source_msg=message,
      footer_content="Post selected for GvG signup.",
    )
    if admin_channel:
      await admin_channel.send(embed=forward_embed)
    else:
      await interaction.response.send_message(embed=forward_embed, ephemeral=True)


async def setup(bot: commands.Bot):
  await bot.add_cog(GvGSignup(bot))
