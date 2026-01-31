import discord
from discord import app_commands
from discord.ext import commands


class Test(commands.Cog):
  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot

  @app_commands.command(name="list_roles", description="List all roles in this server")
  async def list_roles(self, interaction: discord.Interaction):
    if not interaction.guild:
      return await interaction.response.send_message(
        "This can only be used in a server!"
      )

    # Sort roles by position (highest first)
    # Filter out @everyone for a cleaner list
    roles = [
      role.name
      for role in sorted(interaction.guild.roles, reverse=True)
      if not role.is_default()
    ]

    if not roles:
      return await interaction.response.send_message(
        "No custom roles found.", ephemeral=True
      )

    role_list = "\n".join([f"• {name}" for name in roles])

    # Using an embed because role lists can get very long
    embed = discord.Embed(
      title=f"Roles in {interaction.guild.name}",
      description=role_list,
      color=discord.Color.blue(),
    )

    await interaction.response.send_message(embed=embed)

  @app_commands.command(
    name="check_user_roles", description="See what roles a specific member has"
  )
  @app_commands.describe(member="The user to check")
  async def check_user_roles(
    self, interaction: discord.Interaction, member: discord.Member
  ):
    # .roles includes @everyone, so we slice [1:] to skip it or filter is_default()
    roles = [role.mention for role in member.roles if not role.is_default()]

    role_str = ", ".join(roles) if roles else "No custom roles."

    embed = discord.Embed(title=f"Roles for {member.display_name}", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Roles", value=role_str)

    await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
  await bot.add_cog(Test(bot))
