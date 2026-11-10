import httpx

from proxy_manager import GeonodeProxyProvider, ProxyFilter, ProxyScrapeProxyProvider


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
