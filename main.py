import os
from dotenv import load_dotenv

from bot.client import Bot

# Configure env
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
  raise ValueError("Discord token not found in environment variable `DISCORD_TOKEN`.")

if __name__ == "__main__":
  # Configure bot
  bot = Bot()
  bot.run(TOKEN)
