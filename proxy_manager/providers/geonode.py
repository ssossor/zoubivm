"""Geonode proxy provider implementation."""

import logging
import httpx
from typing import Optional, Union

from .base import (BaseProxyProvider, ProxyFilter, ProxyResponse, ProxyData,
                   filter_params, wanted_protocols)

logger = logging.getLogger("proxy_manager.geonode_provider")


class GeonodeProxyProvider(BaseProxyProvider):
    """
    Proxy provider for the Geonode free proxy list (https://geonode.com/free-proxy-list).

    Only proxies with an uptime of at least `min_uptime` percent are returned,
    most recently checked first.
    """

    API_URL = "https://proxylist.geonode.com/api/proxy-list"

    def __init__(self, timeout: int = 30, min_uptime: int = 90):
        """
        Initialize the Geonode proxy provider.

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
        Fetch proxies from the Geonode API.

        Args:
            filters: Filtering options (country, protocols, limit)

        Returns:
            ProxyResponse containing the proxies from Geonode
        """
        filters = filter_params(filters)

        params = {
            "limit": filters.get("limit", 100),
            "page": 1,
            "sort_by": "lastChecked",
            "sort_type": "desc",
            "filterUpTime": self.min_uptime,
        }
        if filters.get("country"):
            params["country"] = filters["country"]
        if filters.get("protocol"):
            params["protocols"] = filters["protocol"]

        try:
            response = await self._client.get(self.API_URL, params=params)
            response.raise_for_status()
            data = response.json()["data"]
        except (httpx.HTTPError, ValueError, KeyError) as e:
            logger.error(f"Error fetching from Geonode: {e!r}")
            return ProxyResponse(proxies=[], total_count=0, filters_applied=params)

        wanted = wanted_protocols(filters)
        proxies = []
        for item in data:
            protocol = next((p for p in wanted if p in item["protocols"]), item["protocols"][0])
            proxies.append(ProxyData(
                address=item["ip"],
                port=int(item["port"]),
                protocol=protocol,
                country_code=item.get("country"),
                timeout_ms=item.get("responseTime"),
            ))

        logger.info(f"Fetched {len(proxies)} proxies from Geonode ({params.get('country', 'all')})")
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
