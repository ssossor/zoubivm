import requests, json, discord
from discord import app_commands
from dotenv import dotenv_values

config = dotenv_values(".env")
print(config)

url = "https://api.www.root-me.org/"

creds = {"api_key": config["api_key"]}

users = {}

# Get challenge from id
def get_challenges(id_challenge: int) -> dict:
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

do_register("Ssor")
print("Ssor registered !")
#do_register("r0g18")
#print("r0g18 registered !")
#do_register("b0tm4n")
#print("b0tm4n registered !")
#
#users["Aube"] = get_auteurs_id(643003)["data"]
#print("Aube registered !")
#
#print(users)

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

@app_commands.command()
async def slash(interaction: discord.Interaction, number: int, string: str):
    await interaction.response.send_message(f'{number=} {string=}', ephemeral=True)

@app_commands.command()
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong!")

@app_commands.command()
async def register(interaction: discord.Interaction, username: str):
    r = do_register(username)
    if r["status"] == "error":
        await interaction.response.send_message(r["data"])
    if r["status"] == "ok":
        await interaction.response.send_message(r["data"])

@app_commands.command()
async def remove(interaction: discord.Interaction, username: str):
    r = do_remove(username)
    if r["status"] == "error":
        await interaction.response.send_message(r["data"])
    if r["status"] == "ok":
        await interaction.response.send_message(r["data"])

@app_commands.command()
async def list(interaction: discord.Interaction):
    await interaction.response.send_message(do_list())

@app_commands.command()
async def profile(interaction: discord.Interaction, username: str):
    r = do_profile(username)
    if r["status"] == "error":
        await interaction.response.send_message(r["data"])
    if r["status"] == "ok":
        await interaction.response.send_message(embed=format_profile(do_profile(username)["data"]))

@app_commands.command()
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.send_message(embed=format_leaderboard())

tree.add_command(slash) # POUQOA CA MARCHE PAS

bot.run(config["token"])

