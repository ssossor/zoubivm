from discord.ext import commands, tasks
from discord import app_commands
import discord
from clients import RootMeClient
from clients.utils import RootMeApiError, RootMeRateLimitError
from zoubiClient import ZoubiClient, ChallengesCache
import asyncio
import httpx
import logging
import inspect
import utils

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class ZoubiCog(commands.Cog):
    def __init__(self, bot, rm_client: RootMeClient, zoubi_client: ZoubiClient,
                 challenges_cache: ChallengesCache, target_channel_id):
        self.bot = bot
        self.rm_client = rm_client
        self.zoubi_client = zoubi_client
        self.challenges_cache = challenges_cache
        self.target_channel_id = target_channel_id

    @tasks.loop(minutes=5)
    async def refresh(self):
        logger.info("Beginning users refresh...")
        all_users = self.zoubi_client.get_all_users()
        new_validations_count = 0

        for user in all_users:
            try:
                fresh_user_data = await self.rm_client.get_author_from_id(user["id_auteur"])
            except (RootMeApiError, RootMeRateLimitError, httpx.HTTPError) as err:
                logger.warning(f"Can't refresh {user['nom']}: {err}")
                continue

            if fresh_user_data["score"] != user["score"]:
                new_validations_count += await self.announce_new_validations(user, fresh_user_data, all_users)

            await asyncio.sleep(2)

        logger.info(f"Users list refreshed! ({new_validations_count} new validations)")

    async def announce_new_validations(self, user, fresh_user_data, all_users) -> int:
        old_ids = {v['id_challenge'] for v in user["validations"]}
        new_validations = [
            v for v in fresh_user_data["validations"] if v['id_challenge'] not in old_ids]

        # kiperZ rapid solve blacklist
        rapid_solve_blacklist = ["758520"]

        announced = 0
        for valid in reversed(new_validations):
            try:
                chall_data = await self.get_challenge(valid['id_challenge'])

                # First blood verification
                solvers = [
                    u for u in all_users
                    if u.get("id_auteur") not in rapid_solve_blacklist
                    and any(v['id_challenge'] == valid['id_challenge'] for v in u.get('validations', []))
                ]
                is_first_blood = not solvers and user["id_auteur"] not in rapid_solve_blacklist
                if is_first_blood:
                    logger.info(f"FIRST BLOOD: by {user['nom']} on {
                                chall_data['titre']} !")

                validation_embed = utils.get_validation_chall_embed(
                    fresh_user_data, valid, chall_data, is_first_blood)
                await self.send_to_target_channel(validation_embed)
            except (RootMeApiError, RootMeRateLimitError, httpx.HTTPError, discord.HTTPException) as err:
                logger.warning(f"Can't announce {valid['titre']} for {user['nom']}, retrying next refresh: {err}")
                return announced

            user["validations"].insert(0, valid)
            self.zoubi_client.save_users_list_to_file()
            announced += 1

        fresh_user_data["profile_id"] = user["profile_id"]
        user.update(fresh_user_data)
        self.zoubi_client.save_users_list_to_file()
        return announced

    async def get_challenge(self, challenge_id: str) -> dict:
        chall_data = self.challenges_cache.get(challenge_id)
        if chall_data is None:
            chall_data = (await self.rm_client.get_chall_from_id(challenge_id))[0]
            self.challenges_cache.add(challenge_id, chall_data)
        return chall_data

    async def send_to_target_channel(self, embed: discord.Embed):
        channel = self.bot.get_channel(self.target_channel_id)
        if channel is None:
            channel = await self.bot.fetch_channel(self.target_channel_id)
        await channel.send(embed=embed)

    @app_commands.command(name="ping", description="Test bot connectivity")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("pong!")

    @app_commands.command(name="register", description="Register your Root-me profile name from URL")
    async def register(self, interaction: discord.Interaction, rootme_profile_id: str):
        await interaction.response.defer(thinking=True)
        try:
            user_id = await self.rm_client.get_user_id(rootme_profile_id)
            if user_id is None:
                await interaction.followup.send(
                    f"I've looked everywhere on Root-Me but there's no `{rootme_profile_id}`...")
                return

            if self.zoubi_client.get_user_from_id(user_id) is not None:
                await interaction.followup.send(
                    f"`{rootme_profile_id}` is already at the adults' table!")
                return

            user_data = await self.rm_client.get_author_from_id(user_id)
            user_data["profile_id"] = rootme_profile_id
            self.zoubi_client.register_user(user_data)

            await interaction.followup.send(
                f"Yo {user_data['nom']}({
                    user_data['id_auteur']}), you're now at the adults' table."
            )
            await interaction.followup.send(embed=utils.get_user_profile_embed(user_data))
        except Exception as err:
            logger.error(err)
            await interaction.followup.send(
                "An error occurred during execution. Please try again later."
            )

    @app_commands.command(name="remove", description="Remove a user from the database")
    async def remove(self, interaction: discord.Interaction, user_id: str):
        try:
            deleted_user_data = self.zoubi_client.remove_user(user_id)

            if deleted_user_data is None:
                await interaction.response.send_message(
                    f"Nope, I've looked everywhere but no `{user_id}` found...")
            else:
                await interaction.response.send_message(
                    f"Goodbye {deleted_user_data['nom']} ({deleted_user_data['id_auteur']})!")
        except Exception as err:
            logger.error(err)
            await interaction.response.send_message("An error occurred, couldn't remove the user from the database")

    @app_commands.command(name="list", description="List all registered users")
    async def list_users(self, interaction: discord.Interaction):
        user_list_message = self.zoubi_client.list_users()
        if len(user_list_message) == 0:
            await interaction.response.send_message("No users registered yet :/")
            return

        chunks = utils.split_message(user_list_message)
        await interaction.response.send_message(chunks[0])
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)

    @app_commands.command(name="profile", description="Display a user's profile")
    async def profile(self, interaction: discord.Interaction, username: str):
        user_data = self.zoubi_client.get_user_from_username(username)
        if user_data is None:
            await interaction.response.send_message(
                f"I've looked everywhere but there's no `{username}` :D")
        else:
            await interaction.response.send_message(embed=utils.get_user_profile_embed(user_data))

    @app_commands.command(name="leaderboard", description="Display the leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        users_list = self.zoubi_client.get_all_users()
        await interaction.response.send_message(embed=utils.get_leaderboard_embed(users_list))

    @commands.command(name="sync")
    async def sync(self, ctx):
        """
        Useful to sync bot commands manually
        """
        try:
            fmt = await self.bot.tree.sync()
            await ctx.send(f"🔄 {len(fmt)} slash commands synchronized!")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @app_commands.command(name="help", description="Display help")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=utils.get_help_embed())
