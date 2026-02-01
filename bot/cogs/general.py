import discord
from discord import app_commands
from discord.ext import commands

from core.database import get_session_context
from core.models import SignupConfig
from services.config import get_signup_config


class General(commands.Cog):
  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot

  @app_commands.command(
    name="peak_role",
    description="Peak a member's role.",
  )
  @app_commands.describe(target="The member you want to look up.")
  async def peak_role(self, interaction: discord.Interaction, target: discord.Member):
    """Peak the role of a member."""
    with get_session_context() as session:
      signup_config: SignupConfig = get_signup_config(session)

    name = target.mention
    roles = [r for r in target.roles if not r.is_default()]
    all_roles_names = [f"<@&{r.id}>" for r in roles]
    gvg_roles_names = [f"<@&{r.id}>" for r in roles if r.id in signup_config.gvg_roles]

    message_str = (
      f"### Role Information for {name}"
      f"\n Roles: {', '.join(all_roles_names)}"
      f"\n GvG Roles: {', '.join(gvg_roles_names)}"
    )

    await interaction.response.send_message(message_str, ephemeral=True)


async def setup(bot: commands.Bot):
  await bot.add_cog(General(bot))
