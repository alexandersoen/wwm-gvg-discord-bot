import discord
from discord import app_commands
from discord.ext import commands

from .ui.role_views import RolePersistenceView


class GvGManage(commands.Cog):
  # TODO: Allow configuration?
  # SIGN_UP_REACT = discord.PartialEmoji.from_str("❤️")
  SIGN_UP_REACT = "❤️"

  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot

    # Define the Context Menu
    self.ctx_menu = app_commands.ContextMenu(
      name="Analyze Sign Up Post",
      callback=self.analyze_sign_up,
    )
    # Add it to the tree
    self.bot.tree.add_command(self.ctx_menu)

    self.admin_channel: discord.TextChannel | None = None
    self.subrole_ids: set[int] = set()

  # -------------------------------------------------------------------------------------

  @app_commands.command(
    name="set_gvg_admin_channel", description="Where to post management messages"
  )
  @app_commands.describe(admin_channel="Set the admin channel")
  async def set_gvg_admin_channel(
    self, interaction: discord.Interaction, admin_channel: discord.TextChannel
  ):
    self.admin_channel = admin_channel

    await interaction.response.send_message(
      f"Admin channel set to: {self.admin_channel}", ephemeral=True
    )

  # -------------------------------------------------------------------------------------

  @app_commands.command(
    name="manage_roles", description="Select roles to track for GvG"
  )
  async def manage_roles(self, interaction: discord.Interaction):
    assert interaction.guild

    # Pass the current set and the guild roles to the view
    view = RolePersistenceView(self.subrole_ids, interaction.guild.roles)
    await interaction.response.send_message(
      "Select GvG class roles:",
      view=view,
      ephemeral=True,
    )

    await view.wait()

    # Update the Cog's state after the view finishes
    if view.confirmed:
      self.subrole_ids = view.temp_role_ids
      await interaction.followup.send(
        f"Updated! Tracking {len(self.subrole_ids)} roles.", ephemeral=True
      )

  # -------------------------------------------------------------------------------------

  async def get_sign_ups(self, message: discord.Message) -> list[int] | None:
    """Get all sign ups (doing this way as bot might not run all the time)."""
    assert self.bot.user

    reaction = discord.utils.get(message.reactions, emoji=self.SIGN_UP_REACT)
    if reaction:
      user_ids = [
        user.id async for user in reaction.users() if user.id != self.bot.user.id
      ]
      return user_ids

  # -------------------------------------------------------------------------------------

  async def analyze_sign_up(
    self, interaction: discord.Interaction, message: discord.Message
  ):
    """Analyze the sign up post."""
    assert message.guild

    if not self.admin_channel:
      await interaction.response.send_message(
        r"Admin channel not setup. Use /set_gvg_admin_channel command.", ephemeral=True
      )
      return

    sign_ups = await self.get_sign_ups(message)
    if not sign_ups:
      await interaction.response.send_message("No sign ups to analyze.", ephemeral=True)
      return

    not_found = 0
    signed_up_members = []
    for user_id in sign_ups:
      user = message.guild.get_member(user_id)

      if not user:
        not_found += 1
        continue

      signed_up_members.append(
        {
          "user_id": user_id,
          "nick": user.nick,
          "roles": [r for r in user.roles if not r.is_default()],
        }
      )

    desc_list = []
    for user_data in signed_up_members:
      nick = user_data["nick"]
      role_str = ", ".join([str(r) for r in user_data["roles"]])

      desc_list.append(f"{nick}: {role_str}")

    embed = discord.Embed(
      title="Sign up summary",
      description="\n".join(desc_list),
      color=discord.Color.dark_blue(),
    )

    await self.admin_channel.send(embed=embed)
    await interaction.response.send_message(
      f"Posted summary to {self.admin_channel.name}", ephemeral=True
    )


# -------------------------------------------------------------------------------------


async def setup(bot: commands.Bot):
  await bot.add_cog(GvGManage(bot))
