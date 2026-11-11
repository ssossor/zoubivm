"""ProxyScrape proxy provider implementation."""

import logging
import httpx
from typing import Optional, Union

from .base import BaseProxyProvider, ProxyFilter, ProxyResponse, ProxyData, filter_params

logger = logging.getLogger("proxy_manager.proxyscrape_provider")


class ProxyScrapeProxyProvider(BaseProxyProvider):
    """
    Proxy provider for the ProxyScrape free proxy list (https://proxyscrape.com/free-proxy-list).

    Only alive proxies with an uptime of at least `min_uptime` percent are returned.
    """

    API_URL = "https://api.proxyscrape.com/v4/free-proxy-list/get"

    def __init__(self, timeout: int = 30, min_uptime: int = 50):
        """
        Initialize the ProxyScrape proxy provider.

        Args:
            timeout: Request timeout in seconds
            min_uptime: Minimum uptime percentage of the returned proxies
        """
        self.timeout = timeout
        self.min_uptime = min_uptime
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def get_proxies(
        self,
        filters: Optional[Union[ProxyFilter, dict]] = None
    ) -> ProxyResponse:
        """
        Fetch proxies from the ProxyScrape API.

        Args:
            filters: Filtering options (country, protocols, limit)

        Returns:
            ProxyResponse containing the proxies from ProxyScrape
        """
        filters = filter_params(filters)

        params = {"request": "display_proxies", "format": "json"}
        for key in ("country", "protocol", "limit"):
            if filters.get(key):
                params[key] = filters[key]

        try:
            response = await self._client.get(self.API_URL, params=params)
            response.raise_for_status()
            data = response.json()["proxies"]
        except (httpx.HTTPError, ValueError, KeyError) as e:
            logger.error(f"Error fetching from ProxyScrape: {e!r}")
            return ProxyResponse(proxies=[], total_count=0, filters_applied=params)

        proxies = [
            ProxyData(
                address=item["ip"],
                port=int(item["port"]),
                protocol=item["protocol"],
                country_code=(item.get("ip_data") or {}).get("countryCode"),
                timeout_ms=round(item["average_timeout"]),
            )
            for item in data
            if item.get("alive") and item.get("uptime", 0) >= self.min_uptime
        ]

        logger.info(f"Fetched {len(proxies)} proxies from ProxyScrape ({params.get('country', 'all')})")
        return ProxyResponse(proxies=proxies, total_count=len(proxies), filters_applied=params)

    async def get_proxies_by_country(
        self,
        country_code: str,
        filters: Optional[Union[ProxyFilter, dict]] = None
    ) -> ProxyResponse:
        """
        Fetch proxies from a specific country.

        Args:
            country_code: Two-letter country code
            filters: Additional filtering options

        Returns:
            ProxyResponse containing proxies from the specified country
        """
        return await self.get_proxies({**filter_params(filters), "country": country_code})

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
