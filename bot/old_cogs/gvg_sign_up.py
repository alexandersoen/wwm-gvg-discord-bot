from typing import Optional
import discord
from datetime import datetime, timedelta
from discord import app_commands
from discord.ext import commands

# -------------------------------------------------------------------------------------


class StickySelect(discord.ui.Select):
  """A dropdown that remembers what was selected."""

  async def callback(self, interaction: discord.Interaction):
    assert self.view

    # Only select one thing
    value = self.values[0]
    for option in self.options:
      option.default = option.value == value

    # Tell the parent View that a value changed
    await self.view.refresh_ui(interaction)


class GvGBuilderView(discord.ui.View):
  DATE_DISPLAY_STR = "%a, %b %d (%Y-%m-%d)"
  DATE_VALUE_STR = "%Y-%m-%d"
  TIME_VALUE_STR = "%H:%M"

  def __init__(self):
    super().__init__(timeout=300)
    self.slots = []

    # Build Date Options (14 days)
    date_opts = []
    for i in range(14):
      label = (datetime.now() + timedelta(days=i)).strftime(self.DATE_DISPLAY_STR)
      value = (datetime.now() + timedelta(days=i)).strftime(self.DATE_VALUE_STR)

      date_selector_opt = discord.SelectOption(label=label, value=value)
      date_opts.append(date_selector_opt)

    # Build Time Options (30 min increments)
    time_opts = []
    for i in range(24):
      m = 720 + 30 * i
      label = f"{m // 60:02d}:{m % 60:02d}"
      value = f"{m // 60:02d}:{m % 60:02d}"

      time_selector_opt = discord.SelectOption(label=label, value=value)
      time_opts.append(time_selector_opt)

    self.date_dropdown = StickySelect(placeholder="Add Date", options=date_opts, row=1)
    self.time_dropdown = StickySelect(placeholder="Add Time", options=time_opts, row=2)

    self.add_item(self.date_dropdown)
    self.add_item(self.time_dropdown)

  async def refresh_ui(self, interaction: discord.Interaction):
    await interaction.response.edit_message(embed=self.make_embed(), view=self)

  def get_date_time(self) -> tuple[Optional[str], Optional[str]]:
    date = self.date_dropdown.values[0] if self.date_dropdown.values else None
    time = self.time_dropdown.values[0] if self.time_dropdown.values else None

    return (date, time)

  def make_embed(self):
    cur_date, cur_time = self.get_date_time()

    desc = "\n".join([f"✅ <t:{s}:F>" for s in sorted(self.slots)]) or "No slots added."
    embed = discord.Embed(title="⚔️ GvG Builder", description=desc, color=0xBEBEFE)
    embed.add_field(name="Current Selection", value=f"📅 `{cur_date}`\n⏰ `{cur_time}`")
    return embed

  @discord.ui.button(label="Add", style=discord.ButtonStyle.blurple, row=3)
  async def add(
    self, interaction: discord.Interaction, _: discord.ui.Button["GvGBuilderView"]
  ):
    cur_date, cur_time = self.get_date_time()
    if cur_date and cur_time:
      dt_str = f"{cur_date} {cur_time}"
      dt = datetime.strptime(dt_str, f"{self.DATE_VALUE_STR} {self.TIME_VALUE_STR}")
      unix_time = int(dt.timestamp())

      # Check uniqueness to add
      if unix_time not in self.slots:
        self.slots.append(unix_time)
        self.slots.sort()

    await interaction.response.edit_message(embed=self.make_embed(), view=self)

  @discord.ui.button(label="Remove Top", style=discord.ButtonStyle.red, row=3)
  async def remove(
    self, interaction: discord.Interaction, _: discord.ui.Button["GvGBuilderView"]
  ):
    if self.slots:
      self.slots.pop()

    await interaction.response.edit_message(embed=self.make_embed(), view=self)

  @discord.ui.button(label="Post", style=discord.ButtonStyle.green, row=3)
  async def post(
    self, interaction: discord.Interaction, _: discord.ui.Button["GvGBuilderView"]
  ):
    self.stop()

    # If the message is already gone, just ignore it
    try:
      await interaction.response.defer()  # Acknowledge the click
      await interaction.delete_original_response()
    except discord.NotFound:
      pass


# -------------------------------------------------------------------------------------


class GvGManager(commands.Cog):
  SIGN_UP_REACT = "❤️"

  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot

    self.target_message_id: int | None = None
    self.target_channel_id: int | None = None
    self.sign_up_set = set()

  @app_commands.command(name="gvg", description="Create new sign up")
  async def new_sign_up(self, interaction: discord.Interaction) -> None:
    """Create a new sign up."""
    # Call sign-up form builder.
    view = GvGBuilderView()
    await interaction.response.send_message(
      "Please select the GvG dates:", embed=view.make_embed(), view=view, ephemeral=True
    )
    await view.wait()

    if not view.slots:
      await interaction.followup.send(
        "No datetime selected, cancelling sign up creation.", ephemeral=True
      )
      return

    # Set up the sign-up post.
    time_str = "Battle Times: \n" + "\n".join(
      [f"<t:{t}:D>: <t:{t}:R>" for t in view.slots]
    )
    embed = discord.Embed(
      title="⚔️ GvG Sign-Up",
      description=f"This weeks GvG Sign-Up. {self.SIGN_UP_REACT} react this message to participate!\n\n"
      + time_str,
      color=discord.Color.blue(),
    )

    # Attempt to actually post it to the channel.
    if interaction.channel and isinstance(interaction.channel, discord.abc.Messageable):
      message = await interaction.channel.send(embed=embed)

      self.target_message_id = message.id
      self.target_channel_id = interaction.channel.id
      await message.add_reaction(self.SIGN_UP_REACT)
    else:
      await interaction.followup.send(
        "Cannot post sign-up in this channel type.", ephemeral=True
      )

  def payload_is_signup_post(
    self, payload: discord.RawReactionActionEvent
  ) -> tuple[int, int] | None:
    """Check if the payload is the sign up post."""
    if (
      self.target_message_id
      and self.target_channel_id
      and payload.message_id == self.target_message_id
    ):
      return (self.target_channel_id, self.target_message_id)

  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
    """Listener on reaction addition to sign up post."""
    post_info = self.payload_is_signup_post(payload)
    if not post_info:
      return

    if str(payload.emoji) == self.SIGN_UP_REACT:
      assert self.bot.user
      if payload.user_id == self.bot.user.id:
        return

      print(f"User id {payload.user_id} has signed up!")

      self.sign_up = await self.get_signups(*post_info)

  @commands.Cog.listener()
  async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
    """Listener on reaction removal to sign up post."""
    post_info = self.payload_is_signup_post(payload)
    if not post_info:
      return

    if str(payload.emoji) == self.SIGN_UP_REACT:
      assert self.bot.user
      if payload.user_id == self.bot.user.id:
        return

      print(f"User id {payload.user_id} has unsigned.")

      self.sign_up = await self.get_signups(*post_info)

  async def get_signups(self, channel_id: int, message_id: int) -> list[int] | None:
    """Get all sign ups (doing this way as bot might not run all the time)."""
    assert self.bot.user

    channel = self.bot.get_channel(channel_id)
    if isinstance(channel, discord.abc.Messageable):
      message = await channel.fetch_message(message_id)
      reaction = discord.utils.get(message.reactions, emoji=self.SIGN_UP_REACT)

      if reaction:
        user_ids = [
          user.id async for user in reaction.users() if user.id != self.bot.user.id
        ]
        return user_ids

    return None


# -------------------------------------------------------------------------------------


async def setup(bot: commands.Bot):
  await bot.add_cog(GvGManager(bot))
