import discord
from discord import app_commands
from discord.ext import commands


class FeedbackForm(discord.ui.Modal, title="Feedback"):
  feedback = discord.ui.TextInput(
    label="What do you think about this bot?",
    style=discord.TextStyle.long,
    placeholder="Type your answer here...",
    required=True,
    max_length=256,
  )

  # We handle the submission logic INSIDE the Modal class
  # This is much cleaner than trying to 'wait' for it in the Cog
  async def on_submit(self, interaction: discord.Interaction):
    # 1. Respond to the user immediately
    await interaction.response.send_message(
      embed=discord.Embed(
        description="Thank you for your feedback! The owners have been notified.",
        color=0xBEBEFE,
      ),
      ephemeral=True,
    )

    # 2. Handle the "Owner Notification" logic
    # We can trigger a custom callback or handle it here
    bot = interaction.client  # Get the bot instance
    app_owner = (await bot.application_info()).owner

    await app_owner.send(
      embed=discord.Embed(
        title="New Feedback",
        description=f"{interaction.user} has submitted feedback:\n```\n{self.feedback.value}\n```",
        color=0xBEBEFE,
      )
    )

# -------------------------------------------------------------------------------------

class Members(commands.Cog):
  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot

  @app_commands.command(name="feedback", description="Submit a feedback form")
  async def feedback(self, interaction: discord.Interaction) -> None:
    # DO NOT defer here. Just send the modal.
    await interaction.response.send_modal(FeedbackForm())


async def setup(bot: commands.Bot):
  await bot.add_cog(Members(bot))
