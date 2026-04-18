import httpx
import asyncio
import logging
import random
from .base import BaseProxyManager
from .free_proxy_server import (
    ProxyClient, 
    AsyncProxyClient,
    ProxyFilter,
    ProxyValidator,
    ProxyRotator,
    ProxyFormatter
)

logger = logging.getLogger("ProxyManager")

class IndustrialZoubiProxy(BaseProxyManager):
    def __init__(self, countries=[], protocol="http", max_timeout=500, working_only=True, limit=30):
        super().__init__()

        self.countries = countries
        self.protocol = protocol
        self.max_timeout = max_timeout
        self.working_only = working_only
        self.limit = limit

        self.filters = ProxyFilter(
            protocol=self.protocol,
            max_timeout=self.max_timeout,
            working_only=self.working_only,
            limit=self.limit
        )
        self.validator = ProxyValidator(
            timeout=10,
            test_url="https://httpbin.org/ip"
        )
        self.rotator = ProxyRotator(self.proxies)
        self.client = AsyncProxyClient(
            base_url="https://free.redscrape.com/api/",
            timeout=30,
            user_agent="free-proxy-server/1.0.0",
        )

    async def _validate_fast(self):
        working = await self.validator.validate_proxies_async(
            self.proxies,
            max_concurrent=20
        )
        return working

    async def get_proxies(self):
        responses = await self.client.get_multiple_countries(
            country_codes=self.countries, 
            filters=self.filters
        )
        self.proxies = [p for resp in responses for p in resp.proxies]

        total_proxies = len(self.proxies)
        self.logger.info(f"Got {total_proxies} individual proxies from {len(self.countries)} countries")

        self.logger.info(f"Selecting only working proxy...")
        if total_proxies > 0:
            self.proxies = await self._validate_fast()
            self.logger.info(f"{len(self.proxies)}/{total_proxies} proxies actually work")

        self.rotator = ProxyRotator(self.proxies)
        await self.rotate()

    async def rotate(self):
        async with self.lock:
            if self.current_proxy is not None:
                self.rotator.remove_proxy(self.current_proxy)

            self.current_proxy = self.rotator.get_next()

            if len(self.proxies) == 0:
                logger.info("No more proxy, refreshing...")
                await self.get_proxies()
            else:
                logger.debug(f"Rotated to next proxy: {str(self.current_proxy)}")
