import pathlib
import discord
from discord.ext import commands


class Bot(commands.Bot):
  def __init__(self) -> None:
    # self.store = storage  # Shared storage access

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.reactions = True

    super().__init__(
      command_prefix="!",
      intents=intents,
      help_command=commands.DefaultHelpCommand(),
    )

  async def setup_hook(self) -> None:
    cog_dir = pathlib.Path("./bot/cogs")
    for ext_path in cog_dir.glob("*.py"):
      ext_name = ext_path.name[:-3]

      await self.load_extension(f"bot.cogs.{ext_name}")
      print(f"Loaded extension: {ext_name}")

    synced = await self.tree.sync()
    print(f"Synced {len(synced)} global commands.")

  async def on_ready(self):
    assert self.user is not None
    print(f"Logged in as {self.user} (ID: {self.user.id})")

bot = Bot()
