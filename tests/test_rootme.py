import pytest

from clients import RootMeRateLimitError


async def test_429_then_success_rotates_key(rm_client, fake_rootme, sleeps):
    fake_rootme.inject("/challenges/", 429, 429)

    data = await rm_client.get_chall_from_id("85")

    assert data[0]["titre"] == "Challenge 85"
    assert sleeps == [5, 10]
    assert {cookie for _, cookie in fake_rootme.calls} == {"api_key=key1", "api_key=key2"}


async def test_persistent_429_raises_without_last_pause(rm_client, fake_rootme, sleeps):
    fake_rootme.inject("/challenges/", 429, 429, 429)

    with pytest.raises(RootMeRateLimitError):
        await rm_client.get_chall_from_id("85")
    assert sleeps == [5, 10]


async def test_retry_after_is_honored(rm_client, fake_rootme, sleeps):
    fake_rootme.inject("/challenges/", (429, {"Retry-After": "7"}))

    await rm_client.get_chall_from_id("85")

    assert sleeps == [7]


async def test_long_retry_after_gives_up(rm_client, fake_rootme, sleeps):
    fake_rootme.inject("/challenges/", (429, {"Retry-After": "120"}))

    with pytest.raises(RootMeRateLimitError):
        await rm_client.get_chall_from_id("85")
    assert sleeps == []
    assert len(fake_rootme.paths("/challenges/")) == 1


async def test_http_date_retry_after_uses_default_pause(rm_client, fake_rootme, sleeps):
    fake_rootme.inject("/challenges/", (429, {"Retry-After": "Wed, 11 Nov 2026 10:00:00 GMT"}))

    await rm_client.get_chall_from_id("85")

    assert sleeps == [5]


async def test_get_user_id(rm_client, fake_rootme):
    assert await rm_client.get_user_id("Aube-643003") == "643003"
    assert fake_rootme.calls == []

    assert await rm_client.get_user_id("Ssor") == "822479"
    assert await rm_client.get_user_id("NewPlayer") == "123456"
    assert await rm_client.get_user_id("unknown-profile") is None
