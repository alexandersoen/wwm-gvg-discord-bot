from typing import Sequence
import discord


class RolePersistenceView(discord.ui.View):
  def __init__(self, current_ids: set[int], all_roles: Sequence[discord.Role]):
    super().__init__(timeout=120)
    self.temp_role_ids = current_ids.copy()
    self.confirmed = False

    # Filter: Only show top 25 roles to fit in one menu, excluding @everyone
    available_roles = [r for r in all_roles if not r.is_default()][:25]

    options = []
    for role in available_roles:
      options.append(
        discord.SelectOption(
          label=role.name,
          value=str(role.id),
          default=role.id in self.temp_role_ids,  # mark currently selected
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
    self.temp_role_ids = {int(val) for val in self.dropdown.values}

    # Ensure UI shows selected
    for option in self.dropdown.options:
      option.default = int(option.value) in self.temp_role_ids

    await interaction.response.edit_message(view=self)

  @discord.ui.button(label="Save", style=discord.ButtonStyle.green)
  async def save(self, interaction: discord.Interaction, _: discord.ui.Button):
    self.confirmed = True
    self.stop()

    # If the message is already gone, just ignore it
    try:
      await interaction.response.defer()  # Acknowledge the click
      await interaction.delete_original_response()
    except discord.NotFound:
      pass
