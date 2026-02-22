import requests, json, discord
from discord.ext import commands, tasks
from dotenv import dotenv_values

config = dotenv_values(".env")
print(config)

url = "https://api.www.root-me.org/"

creds = {"api_key": config["api_key"]}

users = {}

validated_challenges = []

# Get all challenges / Marche pas ?
def get_challenges() -> list:
    r = requests.get(url + "challenges", cookies=creds)
    if r.status_code == 200:
        return {"status": "ok", "data": r.json()}
    else:
        return {"status": "error", "data": "ca marche pas"}

# Get challenge from id
def get_challenges_id(id_challenge: int) -> dict:
    r = requests.get(url + "challenges/" + str(id_challenge), cookies=creds)
    if r.status_code == 200:
        return {"status": "ok", "data": r.json()}
    else:
        return {"status": "error", "data": "ca marche pas"}

# Get list of users from username
def get_auteurs(params: dict) -> list:
    r = requests.get(url + "auteurs", cookies=creds, params=params)
    if r.status_code == 200:
        return {"status": "ok", "data": r.json()}
    else:
        print("aa", r.text)
        return {"status": "error", "data": "ca marche pas (Erreur auteur)"}

# Get profile from id
def get_auteurs_id(id_user: int) -> dict:
    r = requests.get(url + "auteurs/" + str(id_user), cookies=creds)
    #exit(1)
    if r.status_code == 200:
        return {"status": "ok", "data": r.json()}
    else:
        return {"status": "error", "data": "ca marche pas (Erreur auteur id)"}

# Return the correct id from a list of users and a username. Does not work when multiple users have the same username
def parse_users(user_list: list, username: str) -> dict:
    for user in user_list[0]:
        if user_list[0][user]["nom"] == username:
            return user_list[0][user]["id_auteur"]

def do_register(username):
    r = get_auteurs({"nom": username})
    if r["status"] == "ok":
        user_id = parse_users(r["data"], username)
        r2 = get_auteurs_id(user_id)
        if r2["status"] == "ok":
            for i in r2["data"]["validations"]:
                if int(i["id_challenge"]) not in validated_challenges:
                    validated_challenges.append(int(i["id_challenge"]))
            users[username] = r2["data"]
            return {"status": "ok", "data": username + " registered successfully"}
        if r2["status"] == "error":
            return {"status": "error", "data": "ca marche pas (Erreur register)"}
    if r["status"] == "error":
        return r

def do_remove(username):
    if username not in users.keys():
        return {"status": "error", "data": username + " is not registered"}
    return {"status": "ok", "data": username + " has been removed"}

def do_list():
    return "\n".join([key + " | " + users[key] for key in users])

def do_profile(username):
    if username not in users.keys():
        return {"status": "error", "data": username + " is not registered"}

    return {"status": "ok", "data": users[username]}

def format_profile(json: dict) -> discord.Embed:
    title = "Profil de " + json["nom"]
    url = "https://www.root-me.org/" + json["nom"]
    derniers_challs = "- " + json["validations"][0]["titre"] + "\n" + \
                    "- " + json["validations"][1]["titre"] + "\n" + \
                    "- " + json["validations"][2]["titre"]

    description = "**Points :** " + json["score"] + "\n**Derniers challs validés :**\n" + derniers_challs

    embed = discord.Embed(title=title, url=url, description=description, colour=0x00b0f4)

    return embed

def format_leaderboard() -> discord.Embed:
    tmp = []

    for username in users.keys():
        r = do_profile(username)
        if r["status"] == "ok":
            tmp.append({"username": username, "points": r["data"]["score"]})

    newlist = sorted(tmp, key=lambda d: int(d['points']))

    newlist = newlist[:10][::-1]

    emojis = [":first_place:", ":second_place:", ":third_place:", ":four:", ":five:", ":six:", ":seven:", ":eight:", ":nine:", ":keycap_ten:"]
    
    description = ""

    for i in range(len(newlist)):
        description += emojis[i] + " **" + newlist[i]["username"] + "** (" + newlist[i]["points"] + " points)\n"

    embed = discord.Embed(title="Leaderboard", description=description, colour=0x00b0f4)

    return embed

def update_users():
    result = []
    for username in users.keys():
        old = users[username]
        r = get_auteurs_id(int(old["id_auteur"]))
        if r["status"] == "ok":
            new = r["data"]
            if len(old["validations"]) != len(new["validations"]):
                new_challs = new["validations"][:len(new["validations"]) - len(old["validations"])]
                for i in new_challs:
                    if int(i["id_challenge"]) not in validated_challenges:
                        result.append(":drop_of_blood: " + username + " a first blood " + i["titre"] + " ! Félicitations ! :drop_of_blood:")
                        validated_challenges.append(int(i["id_challenge"]))
                    else:
                        result.append(":fire: " + username + " a solve " + i["titre"] + " ! Félicitations ! :fire:")
                users[username] = new
        else:
            pass
    return result

        

#users["stregle"] = {'id_auteur': '1078144', 'nom': 'stregle', 'statut': '6forum', 'logo_url': 'IMG/logo/auton0.png', 'score': '0', 'position': '', 'membre': 'false', 'challenges': [], 'solutions': [], 'validations': []}
#print("stregle registered !")

print("DEBUG", get_auteurs({"nom": "MELO"}))
#do_register("rayzhed")
print(users)
exit(1)

do_register("Ssor")
print("Ssor registered !")
do_register("r0g18")
print("r0g18 registered !")
do_register("b0tm4n")
print("b0tm4n registered !")
users["Aube"] = get_auteurs_id(643003)["data"]
print("Aube registered !")
users["Melo"] = get_auteurs_id(919505)["data"]
print("Melo registered !")


intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

@tasks.loop(minutes=1)
async def refresh():
    print("refresh !")
    channel = bot.get_channel(1470383153376923690)
    news = update_users()
    for new in news:
        await channel.send(new)

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")
    refresh.start()
    try:
        synced = await bot.tree.sync()
        print(f"🔄 {len(synced)} commande(s) slash synchronisée(s)")
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation : {e}")

@bot.tree.command(name="ping", description="test")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong!")

@bot.tree.command(name="register", description="test")
async def register(interaction: discord.Interaction, username: str):
    r = do_register(username)
    if r["status"] == "error":
        await interaction.response.send_message(r["data"])
    if r["status"] == "ok":
        await interaction.response.send_message(r["data"])

@bot.tree.command(name="remove", description="test")
async def remove(interaction: discord.Interaction, username: str):
    r = do_remove(username)
    if r["status"] == "error":
        await interaction.response.send_message(r["data"])
    if r["status"] == "ok":
        await interaction.response.send_message(r["data"])

@bot.tree.command(name="list", description="test")
async def list(interaction: discord.Interaction):
    await interaction.response.send_message(do_list())

@bot.tree.command(name="profile", description="test")
async def profile(interaction: discord.Interaction, username: str):
    r = do_profile(username)
    if r["status"] == "error":
        await interaction.response.send_message(r["data"])
    if r["status"] == "ok":
        await interaction.response.send_message(embed=format_profile(do_profile(username)["data"]))

@bot.tree.command(name="leaderboard", description="test")
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.send_message(embed=format_leaderboard())

if __name__ == "__main__":
    print("🚀 Démarrage du bot Root-Me...")
    bot.run(config["token"])