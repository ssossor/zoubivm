"""stormsia proxy provider implementation."""

import logging
import httpx
from typing import List, Optional, Union

from .base import (BaseProxyProvider, ProxyFilter, ProxyResponse, ProxyData,
                   filter_params, wanted_protocols)

logger = logging.getLogger("proxy_manager.stormsia_provider")


class StormsiaProxyProvider(BaseProxyProvider):
    """
    Proxy provider for the stormsia free proxy list (https://stormsia.github.io/proxy-list).

    The list is re-validated every 15 minutes, with the measured response time of each
    proxy. It is a single file for all countries, downloaded once per fetch.
    """

    API_URL = "https://stormsia.github.io/proxy-list/proxies.json"

    def __init__(self, timeout: int = 30):
        """
        Initialize the stormsia proxy provider.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)

    async def _fetch(self) -> list:
        """Download the whole list, or return [] on error."""
        try:
            response = await self._client.get(self.API_URL)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.error(f"Error fetching from stormsia: {e!r}")
            return []

    def _select(self, items: list, filters: dict) -> ProxyResponse:
        """Keep the items matching the filters, fastest first."""
        wanted = wanted_protocols(filters)
        country = filters.get("country")
        proxies = []
        for item in items:
            try:
                code = item["geolocation"]["country"]["iso_code"]
                if (country and code != country) or (wanted and item["protocol"] not in wanted):
                    continue
                proxies.append(ProxyData(
                    address=item["host"],
                    port=int(item["port"]),
                    protocol=item["protocol"],
                    country_code=code,
                    timeout_ms=round(item["timeout"] * 1000),
                    username=item.get("username"),
                    password=item.get("password"),
                ))
            except (KeyError, TypeError, ValueError):
                continue

        proxies.sort(key=lambda p: p.timeout_ms)
        proxies = proxies[:filters.get("limit")]
        logger.info(f"Fetched {len(proxies)} proxies from stormsia ({country or 'all'})")
        return ProxyResponse(proxies=proxies, total_count=len(proxies), filters_applied=filters)

    async def get_proxies(
        self,
        filters: Optional[Union[ProxyFilter, dict]] = None
    ) -> ProxyResponse:
        """
        Fetch proxies from the stormsia list.

        Args:
            filters: Filtering options (country, protocols, limit)

        Returns:
            ProxyResponse containing the proxies from stormsia
        """
        return self._select(await self._fetch(), filter_params(filters))

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

    async def get_multiple_countries(
        self,
        country_codes: List[str],
        filters: Optional[Union[ProxyFilter, dict]] = None
    ) -> List[ProxyResponse]:
        """
        Fetch proxies for several countries, downloading the list only once.

        Args:
            country_codes: List of two-letter country codes
            filters: Filtering options

        Returns:
            List of ProxyResponse objects (one per country)
        """
        items = await self._fetch()
        filters = filter_params(filters)
        return [self._select(items, {**filters, "country": code}) for code in country_codes]

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
