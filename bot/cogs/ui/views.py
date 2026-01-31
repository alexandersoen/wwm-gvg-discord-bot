from typing import Sequence
import discord


class RolePersistenceView(discord.ui.View):
  def __init__(self, current_ids: list[int], all_roles: Sequence[discord.Role]):
    super().__init__(timeout=120)
    self.role_ids = current_ids.copy()
    self.confirmed = False

    # Filter: Only show top 25 roles to fit in one menu, excluding @everyone
    available_roles = [r for r in all_roles if not r.is_default()][:25]

    options = []
    for role in available_roles:
      options.append(
        discord.SelectOption(
          label=role.name,
          value=str(role.id),
          default=role.id in self.role_ids,  # mark currently selected
        )
      )

    # Create the dropdown
    self.dropdown = discord.ui.Select(
      placeholder="Choose roles...",
      min_values=0,
      max_values=len(available_roles),
      options=options,
    )
    self.dropdown.callback = self.select_callback
    self.add_item(self.dropdown)

  async def select_callback(self, interaction: discord.Interaction):
    # Turn off save until loaded
    self.save.disabled = True
    await interaction.response.edit_message(view=self)

    # Ensure UI shows selected
    self.role_ids = [int(val) for val in self.dropdown.values]
    for option in self.dropdown.options:
      option.default = int(option.value) in self.role_ids

    self.save.disabled = False
    await interaction.edit_original_response(view=self)

  @discord.ui.button(label="Save", style=discord.ButtonStyle.success)
  async def save(self, interaction: discord.Interaction, _: discord.ui.Button):
    self.confirmed = True
    self.stop()

    # If the message is already gone, just ignore it
    try:
      await interaction.response.edit_message(content="Saving...", view=None)
    except discord.NotFound:
      pass


class ReactionSetupView(discord.ui.View):
  def __init__(self, canvas_msg: discord.Message):
    super().__init__(timeout=120)
    self.canvas_msg = canvas_msg
    self.result = set()

  @discord.ui.button(label="Save & Clean Up", style=discord.ButtonStyle.success)
  async def confirm(self, interaction: discord.Interaction, _: discord.ui.Button):
    refreshed_msg = await self.canvas_msg.channel.fetch_message(self.canvas_msg.id)

    #  Extract reactions
    for reaction in refreshed_msg.reactions:
      self.result.add(str(reaction.emoji))

    # Delete the temporary canvas message
    await self.canvas_msg.delete()

    # Final feedback
    await interaction.response.edit_message(
      content=f"Processing reacts: {' '.join(self.result)}", view=None
    )
    self.stop()

  async def on_timeout(self):
    # Cleanup even if the user goes AFK
    try:
      await self.canvas_msg.delete()
    except discord.NotFound:
      pass
