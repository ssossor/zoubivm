import discord
import datetime

BASE_URL = "https://www.root-me.org"


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
