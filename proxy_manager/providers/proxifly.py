"""Proxifly proxy provider implementation."""

import logging
import random
import httpx
from typing import Optional, Union

from .base import (BaseProxyProvider, ProxyFilter, ProxyResponse, ProxyData,
                   filter_params, wanted_protocols)

logger = logging.getLogger("proxy_manager.proxifly_provider")


class ProxiflyProxyProvider(BaseProxyProvider):
    """
    Proxy provider for the Proxifly free proxy list (https://github.com/proxifly/free-proxy-list).

    The list is updated every 5 minutes but gives no response time: when there are more
    proxies than the limit, a random sample is returned, so each fetch tries other ones.
    """

    BASE_URL = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies"

    def __init__(self, timeout: int = 30):
        """
        Initialize the Proxifly proxy provider.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def get_proxies(
        self,
        filters: Optional[Union[ProxyFilter, dict]] = None
    ) -> ProxyResponse:
        """
        Fetch proxies from the Proxifly list.

        Args:
            filters: Filtering options (country, protocols, limit)

        Returns:
            ProxyResponse containing the proxies from Proxifly
        """
        filters = filter_params(filters)
        country = filters.get("country")
        url = f"{self.BASE_URL}/countries/{country}/data.json" if country else f"{self.BASE_URL}/all/data.json"

        try:
            response = await self._client.get(url)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.error(f"Error fetching from Proxifly: {e!r}")
            return ProxyResponse(proxies=[], total_count=0, filters_applied=filters)

        wanted = wanted_protocols(filters)
        proxies = []
        for item in data:
            try:
                if wanted and item["protocol"] not in wanted:
                    continue
                proxies.append(ProxyData(
                    address=item["ip"],
                    port=int(item["port"]),
                    protocol=item["protocol"],
                    country_code=item["geolocation"]["country"],
                ))
            except (KeyError, TypeError, ValueError):
                continue

        limit = filters.get("limit")
        if limit and len(proxies) > limit:
            proxies = random.sample(proxies, limit)

        logger.info(f"Fetched {len(proxies)} proxies from Proxifly ({country or 'all'})")
        return ProxyResponse(proxies=proxies, total_count=len(proxies), filters_applied=filters)

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
