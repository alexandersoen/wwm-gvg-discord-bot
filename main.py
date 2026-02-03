import os
import asyncio
import uvicorn
from dotenv import load_dotenv

from bot.client import bot
from web.app import app
from core.database import init_db

# Configure env
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")


async def run_bot():
  if TOKEN is None:
    raise ValueError("Discord token not found in environment variable `DISCORD_TOKEN`.")

  await bot.start(TOKEN)


async def run_web():
  config = uvicorn.Config(app, host="127.0.0.1", port=8000, loop="asyncio")
  server = uvicorn.Server(config)
  await server.serve()


async def main():
  print("Initializing Database...")
  init_db()

  app.state.bot = bot

  await asyncio.gather(run_bot(), run_web())


if __name__ == "__main__":
  try:
    asyncio.run(main())
  except KeyboardInterrupt:
    pass
