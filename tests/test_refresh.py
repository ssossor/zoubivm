import asyncio

import httpx

from tests.conftest import load_users, stored_user


def challenge_ids(users: list, author_id: str) -> list:
    user = next(u for u in users if u["id_auteur"] == author_id)
    return [v["id_challenge"] for v in user["validations"]]


async def test_new_validations_are_announced_in_order(make_cog, authors, channel, users_file):
    aube, ssor, kiwi = authors
    cog = make_cog([stored_user(aube, missing=2), stored_user(ssor, missing=1), stored_user(kiwi)])

    await cog.refresh()

    assert [e.title for e in channel.sent] == ["Challenge 3", "Challenge 4", "Challenge 6"]
    saved = load_users(users_file)
    assert challenge_ids(saved, "643003") == ["4", "3", "2", "1"]
    assert challenge_ids(saved, "822479") == ["6", "5", "1"]


async def test_first_blood(make_cog, authors, channel):
    aube, ssor, _ = authors
    cog = make_cog([stored_user(aube), stored_user(ssor, missing=2)])

    await cog.refresh()

    assert [e.author.name for e in channel.sent] == ["🩸First🩸Blood ", "🩸First🩸Blood "]


async def test_unknown_author_is_skipped(make_cog, authors, channel, fake_rootme, users_file):
    aube, ssor, kiwi = authors
    cog = make_cog([stored_user(aube), stored_user(ssor, missing=1), stored_user(kiwi)])
    fake_rootme.inject("/auteurs/643003", 404)

    await cog.refresh()

    assert [e.title for e in channel.sent] == ["Challenge 6"]
    assert challenge_ids(load_users(users_file), "822479") == ["6", "5", "1"]


async def test_rootme_unreachable(make_cog, authors, channel, fake_rootme):
    cog = make_cog([stored_user(a, missing=1) for a in authors])
    fake_rootme.inject("/auteurs/", *[httpx.ConnectError("fake outage")] * len(authors))

    await asyncio.wait_for(cog.refresh(), timeout=5)

    assert len(fake_rootme.paths("/auteurs/")) == len(authors)
    assert channel.sent == []


async def test_rate_limit_during_announces_resumes_next_cycle(make_cog, authors, channel,
                                                              fake_rootme, users_file):
    aube = authors[0]
    cog = make_cog([stored_user(aube, missing=3)])
    fake_rootme.inject("/challenges/3", 429, 429, 429)

    await cog.refresh()

    assert [e.title for e in channel.sent] == ["Challenge 2"]
    assert challenge_ids(load_users(users_file), "643003") == ["2", "1"]

    await cog.refresh()

    assert [e.title for e in channel.sent] == ["Challenge 2", "Challenge 3", "Challenge 4"]
    assert challenge_ids(load_users(users_file), "643003") == ["4", "3", "2", "1"]


async def test_discord_refusal_resumes_next_cycle(make_cog, authors, channel, users_file):
    ssor = authors[1]
    cog = make_cog([stored_user(ssor, missing=2)])
    channel.fail_next = 1

    await cog.refresh()

    assert channel.sent == []
    assert challenge_ids(load_users(users_file), "822479") == ["1"]

    await cog.refresh()

    assert [e.title for e in channel.sent] == ["Challenge 5", "Challenge 6"]
    assert challenge_ids(load_users(users_file), "822479") == ["6", "5", "1"]


async def test_cached_challenge_is_not_fetched(make_cog, authors, channel, fake_rootme):
    aube = authors[0]
    cog = make_cog([stored_user(aube, missing=1)])
    cog.challenges_cache.add("4", {"titre": "Challenge 4", "score": "20",
                                   "url_challenge": "fr/Challenges/4"})

    await cog.refresh()

    assert [e.title for e in channel.sent] == ["Challenge 4"]
    assert fake_rootme.paths("/challenges/") == []


async def test_fetched_challenge_is_cached(make_cog, authors, fake_rootme):
    aube = authors[0]
    cog = make_cog([stored_user(aube, missing=1)])

    await cog.refresh()

    assert cog.challenges_cache.get("4")["url_challenge"] == "fr/Challenges/4"
    assert fake_rootme.paths("/challenges/") == ["/challenges/4"]


async def test_scheduled_task_survives_outage(make_cog, authors, fake_rootme):
    cog = make_cog([stored_user(a) for a in authors])
    fake_rootme.inject("/auteurs/", *[httpx.ConnectError("fake outage")] * len(authors))

    cog.refresh.start()
    for _ in range(50):
        await asyncio.sleep(0.05)
        if len(fake_rootme.paths("/auteurs/")) == len(authors) or cog.refresh.failed():
            break
    await asyncio.sleep(0.05)
    running = cog.refresh.is_running() and not cog.refresh.failed()
    cog.refresh.cancel()

    assert len(fake_rootme.paths("/auteurs/")) == len(authors)
    assert running


async def test_log_channel_on_total_failure_and_recovery(make_cog, authors, channel,
                                                         log_channel, fake_rootme):
    cog = make_cog([stored_user(a) for a in authors])
    outage = [httpx.ConnectError("fake outage")] * len(authors)

    fake_rootme.inject("/auteurs/", *outage)
    await cog.refresh()
    fake_rootme.inject("/auteurs/", *outage)
    await cog.refresh()
    await cog.refresh()

    assert len(log_channel.texts) == 2
    assert log_channel.texts[0].startswith("⚠️ Refresh failed for all 3 users")
    assert log_channel.texts[1] == "✅ Refresh works again"
    assert channel.texts == []


async def test_partial_failure_is_not_logged(make_cog, authors, log_channel, fake_rootme):
    cog = make_cog([stored_user(a) for a in authors])
    fake_rootme.inject("/auteurs/643003", httpx.ConnectError("fake outage"))

    await cog.refresh()

    assert log_channel.texts == []


async def test_stopped_task_is_logged(make_cog, log_channel):
    cog = make_cog([])

    await cog.refresh_error(RuntimeError("boom"))

    assert log_channel.texts == ["🛑 Refresh task stopped: RuntimeError('boom')"]


async def test_log_channel_errors_are_swallowed(make_cog, log_channel):
    cog = make_cog([])
    log_channel.fail_next = 1

    await cog.send_log("hello")

    assert log_channel.texts == []
