import asyncio

import httpx

import pytest

from proxy_manager import (GeonodeProxyProvider, ProxiflyProxyProvider, ProxyData,
                           ProxyFilter, ProxyScrapeProxyProvider, ProxyValidator,
                           StormsiaProxyProvider, TorProxyProvider)

ALL_PROTOCOLS = ProxyFilter(protocol="socks5,http,https", limit=30)


def mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def geonode_proxy(ip: str, protocols: list, response_time: int) -> dict:
    return {"ip": ip, "port": "1080", "protocols": protocols, "country": "FR",
            "upTime": 100, "responseTime": response_time}


async def test_geonode_proxies_by_country():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": [
            geonode_proxy("10.0.0.1", ["socks4", "socks5"], 120),
            geonode_proxy("10.0.0.2", ["http"], 80),
        ]})

    provider = GeonodeProxyProvider()
    provider._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    response = await provider.get_proxies_by_country(
        "FR", ProxyFilter(protocol="socks5", limit=30))
    await provider.close()

    params = requests[0].url.params
    assert params["country"] == "FR"
    assert params["protocols"] == "socks5"
    assert params["limit"] == "30"
    assert params["filterUpTime"] == "90"
    assert [p.url for p in response] == ["socks5://10.0.0.1:1080", "http://10.0.0.2:1080"]
    assert [p.timeout_ms for p in response] == [120, 80]


async def test_geonode_error_returns_no_proxies():
    provider = GeonodeProxyProvider()
    provider._client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(503)))

    response = await provider.get_proxies()
    await provider.close()

    assert response.proxies == []


async def test_proxyscrape_keeps_alive_proxies_with_uptime():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"proxies": [
            {"ip": "10.0.0.1", "port": 1080, "protocol": "socks5", "alive": True,
             "uptime": 90.5, "average_timeout": 420.7, "ip_data": {"countryCode": "DE"}},
            {"ip": "10.0.0.2", "port": 1080, "protocol": "socks5", "alive": True,
             "uptime": 20.0, "average_timeout": 300.0},
            {"ip": "10.0.0.3", "port": 1080, "protocol": "socks5", "alive": False,
             "uptime": 99.0, "average_timeout": 100.0},
        ]})

    provider = ProxyScrapeProxyProvider()
    provider._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    response = await provider.get_proxies_by_country("DE", ProxyFilter(protocol="socks5"))
    await provider.close()

    params = requests[0].url.params
    assert (params["country"], params["protocol"]) == ("DE", "socks5")
    assert [(p.url, p.country_code, p.timeout_ms) for p in response] == [
        ("socks5://10.0.0.1:1080", "DE", 421)]


async def test_validator_keeps_working_proxies_with_measured_time(monkeypatch):
    delays = {"10.0.0.1": 0.05, "10.0.0.2": 0.01}

    async def fake_validate(self, proxy, session=None):
        await asyncio.sleep(delays.get(proxy.address, 0))
        return proxy.address in delays

    monkeypatch.setattr(ProxyValidator, "validate_proxy", fake_validate)
    proxies = [ProxyData("10.0.0.1", 1080, "socks5", timeout_ms=10),
               ProxyData("10.0.0.2", 1080, "socks5", timeout_ms=900),
               ProxyData("10.0.0.3", 1080, "socks5", timeout_ms=5)]

    working = await ProxyValidator().validate_proxies(proxies)

    assert [p.address for p in working] == ["10.0.0.1", "10.0.0.2"]
    assert working[0].timeout_ms >= 50
    assert working[1].timeout_ms < 50


def test_proxy_url_with_credentials_is_hidden_in_repr():
    proxy = ProxyData("tor", 9050, "socks5", username="user", password="p@ss")

    assert proxy.url == "socks5://user:p%40ss@tor:9050"
    assert "user" not in repr(proxy) and "p@ss" not in repr(proxy)
    assert ProxyData("10.0.0.1", 1080, "socks5").url == "socks5://10.0.0.1:1080"


async def test_tor_gives_one_proxy_per_new_circuit():
    provider = TorProxyProvider("socks5://tor:9050", circuits=3)

    first = (await provider.get_multiple_countries(["FR", "DE", "NL"]))
    second = await provider.get_proxies()
    await provider.close()

    assert len(first) == 1
    proxies = first[0].proxies + second.proxies
    assert {(p.address, p.port, p.protocol) for p in proxies} == {("tor", 9050, "socks5")}
    assert len({(p.username, p.password) for p in proxies}) == 6


@pytest.mark.parametrize("url", ["tor:9050", "http://tor:9050", "socks5://tor"])
def test_tor_rejects_invalid_url(url):
    with pytest.raises(ValueError):
        TorProxyProvider(url)


def test_https_proxy_is_reached_with_http():
    assert ProxyData("10.0.0.1", 8080, "https").url == "http://10.0.0.1:8080"
    assert ProxyData("10.0.0.1", 8080, "http").url == "http://10.0.0.1:8080"


async def test_geonode_picks_preferred_protocol():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": [
            geonode_proxy("10.0.0.1", ["https", "http"], 120),
            geonode_proxy("10.0.0.2", ["https"], 80),
            geonode_proxy("10.0.0.3", ["http", "socks5"], 50),
        ]})

    provider = GeonodeProxyProvider()
    provider._client = mock_client(handler)

    response = await provider.get_proxies(ALL_PROTOCOLS)
    await provider.close()

    assert requests[0].url.params["protocols"] == "socks5,http,https"
    assert [p.protocol for p in response] == ["http", "https", "socks5"]
    assert [p.url for p in response] == ["http://10.0.0.1:1080", "http://10.0.0.2:1080",
                                         "socks5://10.0.0.3:1080"]


def stormsia_proxy(host: str, protocol: str, country: str, timeout: float) -> dict:
    return {"protocol": protocol, "username": None, "password": None, "host": host,
            "port": 1080, "timeout": timeout, "exit_ip": host,
            "geolocation": {"country": {"iso_code": country}}}


async def test_stormsia_downloads_once_and_splits_by_country():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[
            stormsia_proxy("10.0.0.1", "socks5", "FR", 0.9),
            stormsia_proxy("10.0.0.2", "http", "FR", 0.2),
            stormsia_proxy("10.0.0.3", "socks4", "FR", 0.1),
            stormsia_proxy("10.0.0.4", "socks5", "DE", 0.5),
            stormsia_proxy("10.0.0.5", "socks5", "US", 0.1),
            {"protocol": "socks5", "host": "10.0.0.6"},
        ])

    provider = StormsiaProxyProvider()
    provider._client = mock_client(handler)

    fr, de, it = await provider.get_multiple_countries(["FR", "DE", "IT"], ALL_PROTOCOLS)
    await provider.close()

    assert len(requests) == 1
    assert [(p.address, p.protocol, p.timeout_ms) for p in fr] == [
        ("10.0.0.2", "http", 200), ("10.0.0.1", "socks5", 900)]
    assert [p.address for p in de] == ["10.0.0.4"]
    assert it.proxies == []


async def test_stormsia_error_returns_no_proxies():
    provider = StormsiaProxyProvider()
    provider._client = mock_client(lambda _: httpx.Response(503))

    responses = await provider.get_multiple_countries(["FR", "DE"], ALL_PROTOCOLS)
    await provider.close()

    assert [r.proxies for r in responses] == [[], []]


def proxifly_proxy(ip: str, protocol: str) -> dict:
    return {"proxy": f"{protocol}://{ip}:1080", "protocol": protocol, "ip": ip,
            "port": 1080, "https": protocol == "https", "anonymity": "transparent",
            "score": 1, "geolocation": {"country": "DE", "city": "Berlin"}}


async def test_proxifly_proxies_by_country():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[
            proxifly_proxy("10.0.0.1", "socks5"),
            proxifly_proxy("10.0.0.2", "https"),
            proxifly_proxy("10.0.0.3", "socks4"),
            {"protocol": "http", "ip": "10.0.0.4"},
        ])

    provider = ProxiflyProxyProvider()
    provider._client = mock_client(handler)

    response = await provider.get_proxies_by_country("DE", ALL_PROTOCOLS)
    await provider.close()

    assert requests[0].url.path.endswith("/proxies/countries/DE/data.json")
    assert [(p.url, p.country_code) for p in response] == [
        ("socks5://10.0.0.1:1080", "DE"), ("http://10.0.0.2:1080", "DE")]


async def test_proxifly_samples_above_limit():
    data = [proxifly_proxy(f"10.0.1.{i}", "socks5") for i in range(50)]
    provider = ProxiflyProxyProvider()
    provider._client = mock_client(lambda _: httpx.Response(200, json=data))

    response = await provider.get_proxies(ProxyFilter(protocol="socks5", limit=10))
    await provider.close()

    assert len(response.proxies) == 10
    assert len({p.address for p in response}) == 10


async def test_proxifly_unknown_country_returns_no_proxies():
    provider = ProxiflyProxyProvider()
    provider._client = mock_client(lambda _: httpx.Response(404, text="404: Not Found"))

    response = await provider.get_proxies_by_country("LU", ALL_PROTOCOLS)
    await provider.close()

    assert response.proxies == []
