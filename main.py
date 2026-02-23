import discord
from rootmeClient import RootMeClient
from zoubiClient import ZoubiClient
from discord.ext import commands
from dotenv import dotenv_values
import logging
from cogs.zoubi_cog import ZoubiCog

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

config = dotenv_values(".env")
logger.debug(config)

ROOT_ME_API_KEY = config["ROOT_ME_API_KEY"]
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
        logger.info(f"✅ Bot logged in as {bot.user}")
        cog = self.get_cog("ZoubiCog")
        if cog and not cog.refresh.is_running():
            cog.refresh.start()


if __name__ == "__main__":
    logger.info('Initializing clients...')
    rm_client = RootMeClient(ROOT_ME_API_KEY)
    zoubi_client = ZoubiClient(USERS_LIST_FILE)
    bot = DiscordBot(rm_client, zoubi_client, int(TARGET_CHANNEL_ID))

    logger.info(
        "🚀 Démarrage duuuuue la ZoubiVM, bip bipb boubpoubp ARM boupbipbbip HELP bipbipbipbipbipbiiiiiiiiiiiiiip")
    bot.run(DISCORD_TOKEN)
