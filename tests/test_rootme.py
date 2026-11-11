from types import SimpleNamespace

import httpx
import pytest

from clients import RootMeClient, RootMeRateLimitError, describe_error
from proxy_manager import ProxyData, ProxyResponse, ProxyValidator


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


def fake_provider(proxies: list) -> SimpleNamespace:
    provider = SimpleNamespace(fetches=0)

    async def get_multiple_countries(**_):
        provider.fetches += 1
        return [ProxyResponse(list(proxies))]

    async def close():
        pass

    provider.get_multiple_countries = get_multiple_countries
    provider.close = close
    return provider


@pytest.fixture
def provider(monkeypatch) -> SimpleNamespace:
    async def all_working(self, proxies, max_concurrent=20):
        return list(proxies)

    monkeypatch.setattr(ProxyValidator, "validate_proxies", all_working)
    return fake_provider([ProxyData("10.0.0.3", 1080, "socks5", timeout_ms=200),
                          ProxyData("10.0.0.1", 1080, "socks5", timeout_ms=50),
                          ProxyData("10.0.0.2", 1080, "socks5", timeout_ms=100),
                          ProxyData("10.0.0.4", 1080, "socks5", timeout_ms=150)])


@pytest.fixture
async def proxied_client(fake_rootme, sleeps, provider) -> RootMeClient:
    client = await RootMeClient.create(api_keys=["key1", "key2"], proxy_provider=provider)
    yield client
    await client.close()


def current_address(client: RootMeClient) -> str | None:
    proxy = client.proxy_manager.get_current_proxy()
    return proxy.address if proxy else None


async def test_starts_without_proxy(proxied_client, provider, fake_rootme):
    await proxied_client.get_chall_from_id("85")

    assert current_address(proxied_client) is None
    assert provider.fetches == 0


async def test_429_switches_to_best_proxy_and_key(proxied_client, provider, fake_rootme, sleeps):
    fake_rootme.inject("/challenges/", 429)

    data = await proxied_client.get_chall_from_id("85")

    assert data[0]["titre"] == "Challenge 85"
    assert provider.fetches == 1
    assert current_address(proxied_client) == "10.0.0.1"
    assert [cookie for _, cookie in fake_rootme.calls] == ["api_key=key1", "api_key=key2"]
    assert sleeps == []


async def test_proxy_failure_rotates_to_next_proxy(proxied_client, fake_rootme, sleeps):
    fake_rootme.inject("/challenges/", 429, httpx.ProxyError("down"))

    await proxied_client.get_chall_from_id("85")

    assert current_address(proxied_client) == "10.0.0.2"
    assert sleeps == []


async def test_three_failed_proxies_give_up_and_wait(proxied_client, fake_rootme, sleeps):
    fake_rootme.inject("/challenges/", 429)
    await proxied_client.get_chall_from_id("85")
    fake_rootme.inject("/challenges/", httpx.ProxyError("down"), 429, httpx.ConnectTimeout("slow"))

    with pytest.raises(RootMeRateLimitError):
        await proxied_client.get_chall_from_id("85")
    assert len(fake_rootme.paths("/challenges/")) == 5
    assert current_address(proxied_client) == "10.0.0.3"
    assert sleeps == [RootMeClient.PROXY_GIVE_UP_PAUSE]


async def test_fallback_providers_are_tried_in_order(fake_rootme, sleeps, provider):
    empty, also_empty = fake_provider([]), fake_provider([])
    unused = fake_provider([ProxyData("10.0.0.9", 1080, "socks5")])
    client = await RootMeClient.create(api_keys=["key1"], proxy_provider=empty,
                                       fallback_proxy_providers=[also_empty, provider, unused])
    fake_rootme.inject("/challenges/", 429)

    await client.get_chall_from_id("85")
    await client.close()

    assert [p.fetches for p in (empty, also_empty, provider, unused)] == [1, 1, 1, 0]
    assert current_address(client) == "10.0.0.1"


async def test_connection_failure_switches_to_best_proxy(proxied_client, provider,
                                                         fake_rootme, sleeps):
    fake_rootme.inject("/challenges/", httpx.ConnectError(""))

    data = await proxied_client.get_chall_from_id("85")

    assert data[0]["titre"] == "Challenge 85"
    assert provider.fetches == 1
    assert current_address(proxied_client) == "10.0.0.1"
    assert sleeps == []


async def test_connection_failure_without_proxy_raises(rm_client, fake_rootme):
    fake_rootme.inject("/challenges/", httpx.ConnectError("down"))

    with pytest.raises(httpx.ConnectError):
        await rm_client.get_chall_from_id("85")
    assert len(fake_rootme.paths("/challenges/")) == 1


def test_describe_error_shows_hidden_cause():
    try:
        try:
            raise ConnectionResetError(104, "Connection reset by peer")
        except ConnectionResetError as cause:
            raise httpx.ConnectError("") from cause
    except httpx.ConnectError as err:
        description = describe_error(err)

    assert description == "ConnectError('') <- ConnectionResetError(104, 'Connection reset by peer')"


async def test_proxies_are_tested_against_rootme(rm_client):
    assert rm_client.proxy_manager.validator.test_url == "https://api.www.root-me.org/"


async def test_proxies_of_every_supported_protocol_are_asked(rm_client):
    assert rm_client.proxy_manager.filters.protocol == "socks5,http,https"
