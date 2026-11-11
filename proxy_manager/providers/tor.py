"""Tor proxy provider implementation."""

import logging
import secrets
from typing import List, Optional, Union
from urllib.parse import urlsplit

from .base import BaseProxyProvider, ProxyFilter, ProxyResponse, ProxyData

logger = logging.getLogger("proxy_manager.tor_provider")


class TorProxyProvider(BaseProxyProvider):
    """
    Proxy provider for a Tor SOCKS proxy.

    Each returned proxy has its own random SOCKS credentials. Tor isolates streams
    by credentials (IsolateSOCKSAuth, on by default), so each proxy gets its own
    circuit and usually its own exit IP. Every fetch gives new circuits.
    """

    def __init__(self, url: str = "socks5://127.0.0.1:9050", circuits: int = 5):
        """
        Initialize the Tor proxy provider.

        Args:
            url: SOCKS URL of the Tor proxy, e.g. socks5://tor:9050
            circuits: Number of proxies (circuits) returned by each fetch
        """
        parsed = urlsplit(url)
        if parsed.scheme != "socks5" or not parsed.hostname or not parsed.port:
            raise ValueError(f"Tor proxy URL must look like socks5://host:port, got {url!r}")
        self.host = parsed.hostname
        self.port = parsed.port
        self.circuits = circuits

    async def get_proxies(
        self,
        filters: Optional[Union[ProxyFilter, dict]] = None
    ) -> ProxyResponse:
        """
        Return one proxy per new Tor circuit. Filters are ignored.

        Args:
            filters: Ignored, Tor picks its own exits

        Returns:
            ProxyResponse containing the Tor proxies
        """
        proxies = [
            ProxyData(
                address=self.host,
                port=self.port,
                protocol="socks5",
                username=secrets.token_hex(8),
                password=secrets.token_hex(8),
            )
            for _ in range(self.circuits)
        ]
        logger.info(f"Prepared {len(proxies)} Tor circuits")
        return ProxyResponse(proxies=proxies, total_count=len(proxies))

    async def get_proxies_by_country(
        self,
        country_code: str,
        filters: Optional[Union[ProxyFilter, dict]] = None
    ) -> ProxyResponse:
        """
        Same as get_proxies: Tor exits are not chosen by country.

        Args:
            country_code: Ignored
            filters: Ignored

        Returns:
            ProxyResponse containing the Tor proxies
        """
        return await self.get_proxies(filters)

    async def get_multiple_countries(
        self,
        country_codes: List[str],
        filters: Optional[Union[ProxyFilter, dict]] = None
    ) -> List[ProxyResponse]:
        """
        Return a single set of circuits, whatever the number of countries.

        Args:
            country_codes: Ignored
            filters: Ignored

        Returns:
            List with one ProxyResponse
        """
        return [await self.get_proxies(filters)]

    async def close(self):
        """Nothing to close."""
        pass
