from types import SimpleNamespace

import discord

import utils
from cogs.zoubi_cog import ZoubiCog
from tests.conftest import FakeInteraction, stored_user


async def test_register_new_user(make_cog, authors):
    cog = make_cog([stored_user(authors[0])])
    interaction = FakeInteraction()

    await ZoubiCog.register.callback(cog, interaction, "NewPlayer")

    assert cog.zoubi_client.get_user_from_id("123456")["profile_id"] == "NewPlayer"
    assert "adults' table" in interaction.texts()[0]
    assert isinstance(interaction.messages[1][1], discord.Embed)


async def test_register_unknown_profile(make_cog, authors):
    cog = make_cog([stored_user(authors[0])])
    interaction = FakeInteraction()

    await ZoubiCog.register.callback(cog, interaction, "nobody-here")

    assert len(cog.zoubi_client.get_all_users()) == 1
    assert "no `nobody-here`" in interaction.texts()[0]


async def test_register_already_registered(make_cog, authors):
    cog = make_cog([stored_user(authors[0])])
    interaction = FakeInteraction()

    await ZoubiCog.register.callback(cog, interaction, "Aube-643003")

    assert len(cog.zoubi_client.get_all_users()) == 1
    assert "already" in interaction.texts()[0]


def many_users(count: int) -> list:
    return [{"nom": f"player{i:03d}", "score": str(10000 - i), "id_auteur": str(900000 + i),
             "profile_id": f"player{i:03d}", "validations": []} for i in range(count)]


async def test_list_is_split_in_discord_sized_messages(make_cog):
    cog = make_cog(many_users(150))
    interaction = FakeInteraction()

    await ZoubiCog.list_users.callback(cog, interaction)

    messages = interaction.texts()
    assert len(messages) > 1
    assert all(len(m) <= 2000 for m in messages)
    assert "".join(messages).count("player") == 150


def test_leaderboard_is_truncated():
    embed = utils.get_leaderboard_embed(many_users(150))

    assert len(embed.description) <= 4096
    assert embed.description.startswith(":first_place: **player000**")


async def test_sync_ignores_arguments(make_cog):
    cog = make_cog([])
    sent = []

    async def sync():
        return [1, 2, 3]

    async def send(content):
        sent.append(content)

    cog.bot.tree.sync = sync
    await ZoubiCog.sync.callback(cog, SimpleNamespace(send=send))

    assert ZoubiCog.sync.clean_params == {}
    assert ZoubiCog.sync.ignore_extra
    assert sent == ["🔄 3 slash commands synchronized!"]
