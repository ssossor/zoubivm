import discord
import asyncio
from clients import RootMeClient
from zoubiClient import ZoubiClient
from discord.ext import commands
from dotenv import dotenv_values
import logging
import os
from cogs.zoubi_cog import ZoubiCog

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

config = dotenv_values(".env")
logger.debug(config)

# Load RootMe API keys from JSON file
ROOT_ME_API_KEYS_FILE = config.get("ROOT_ME_API_KEYS_FILE", "rootme_api_keys.json")

# Load API keys
if os.path.exists(ROOT_ME_API_KEYS_FILE):
    api_keys = RootMeClient.load_api_keys_from_file(ROOT_ME_API_KEYS_FILE)
    logger.info(f"Loaded {len(api_keys)} API keys from {ROOT_ME_API_KEYS_FILE}")
elif os.path.exists("rootme_api_keys.json"):
    api_keys = RootMeClient.load_api_keys_from_file()
    logger.info(f"Loaded {len(api_keys)} API keys from default file")
else:
    raise FileNotFoundError("No RootMe API keys found. Create rootme_api_keys.json or set ROOT_ME_API_KEYS_FILE in .env")

DISCORD_TOKEN = config["DISCORD_TOKEN"]
TARGET_CHANNEL_ID = config["TARGET_CHANNEL_ID"]
USERS_LIST_FILE = config["USERS_LIST_FILE"]


class DiscordBot(commands.Bot):
    def __init__(self, rm_client, zoubi_client, target_channel_id):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix='!', intents=intents)
        self.rm_client = rm_client
        self.zoubi_client = zoubi_client
        self.target_channel_id = target_channel_id

    async def setup_hook(self):
        await self.add_cog(ZoubiCog(self, self.rm_client, self.zoubi_client, self.target_channel_id))

    async def on_ready(self):
        logger.info(f"✅ Bot logged in as {self.user}")
        cog = self.get_cog("ZoubiCog")
        if cog and not cog.refresh.is_running():
            cog.refresh.start()


async def start_bot():
    logger.info('Initializing clients...')
    rm_client = await RootMeClient.create(api_keys=api_keys)
    zoubi_client = ZoubiClient(USERS_LIST_FILE)
    bot = DiscordBot(rm_client, zoubi_client, int(TARGET_CHANNEL_ID))

    logger.info(
        "🚀 Starting ZoubiVM, bip bipb boubpoubp ARM boupbipbbip HELP bipbipbipbipbipbiiiiiiiiiiiiiip")
    async with bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
