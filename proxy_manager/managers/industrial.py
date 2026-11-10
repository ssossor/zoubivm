"""Advanced proxy manager with pluggable proxy providers."""

import asyncio
import logging
import random
from typing import List

from ..base import BaseProxyManager
from ..providers.base import BaseProxyProvider, ProxyData, ProxyFilter, ProxyResponse
from ..utils import ProxyValidator, ProxyRotator, ProxyFormatter

logger = logging.getLogger("ProxyManager")


class IndustrialZoubiProxy(BaseProxyManager):
    """
    Advanced proxy manager with pluggable proxy providers.
    
    Features:
    - Uses a pluggable proxy provider (via dependency injection)
    - Validates proxies by making real HTTP requests
    - Supports multi-country proxy fetching
    - Gracefully handles the case when no proxies are available
    
    Usage:
        # With default provider (RedScrape)
        proxy_manager = IndustrialZoubiProxy(
            countries=["US", "FR"],
            protocol="socks5"
        )
        
        # With custom provider
        from proxy_manager.proxy_provider import BaseProxyProvider
        custom_provider = MyCustomProvider()
        proxy_manager = IndustrialZoubiProxy(
            countries=["US"],
            proxy_provider=custom_provider
        )
    """
    
    def __init__(
        self, 
        countries=None,
        protocol="http", 
        max_timeout=500,
        working_only=True,
        limit=30,
        proxy_provider=None,
        fallback_provider=None
    ):
        """
        Initialize IndustrialZoubiProxy.
        
        Args:
            countries: List of country codes to fetch proxies from
            protocol: Proxy protocol (http, socks5, etc.)
            max_timeout: Maximum timeout in milliseconds
            working_only: Only use proxies marked as working
            limit: Maximum number of proxies per country
            proxy_provider: A BaseProxyProvider implementation (optional)
                           If None, uses RedScrapeProxyProvider as default
            fallback_provider: Provider used when the main one gives no working
                               proxy (optional)
        """
        super().__init__()
        
        self.countries = countries or []
        self.protocol = protocol
        self.max_timeout = max_timeout
        self.working_only = working_only
        self.limit = limit
        
        # Create filters
        self.filters = ProxyFilter(
            protocol=self.protocol,
            max_timeout=self.max_timeout,
            working_only=self.working_only,
            limit=self.limit
        )
        
        # Use provided provider or default to RedScrape
        if proxy_provider is not None:
            self.provider = proxy_provider
        else:
            from ..providers.redscrape import RedScrapeProxyProvider
            self.provider = RedScrapeProxyProvider(timeout=30)
        self.fallback_provider = fallback_provider
        
        # Initialize utilities
        self.validator = ProxyValidator(
            timeout=10,
            test_url="https://httpbin.org/ip"
        )
        self.rotator = ProxyRotator(self.proxies)
        self.current_index = 0
    
    async def _validate_fast(self) -> List[ProxyData]:
        """Validate all proxies and return only working ones."""
        if not self.proxies:
            return []
        
        working = await self.validator.validate_proxies(
            self.proxies,
            max_concurrent=20
        )
        return working
    
    async def _fetch_working(self, provider: BaseProxyProvider) -> List[ProxyData]:
        """Fetch proxies from a provider and return the working ones, fastest first."""
        try:
            if self.countries:
                # Fetch from multiple countries
                responses = await provider.get_multiple_countries(
                    country_codes=self.countries,
                    filters=self.filters
                )
                
                # Flatten the responses
                self.proxies = []
                for response in responses:
                    self.proxies.extend(response.proxies)
            else:
                # Fetch all proxies
                response = await provider.get_proxies(self.filters)
                self.proxies = response.proxies

            total_proxies = len(self.proxies)
            self.logger.info(f"Got {total_proxies} individual proxies from {len(self.countries) or 'all'} countries")

            if total_proxies == 0:
                self.logger.warning("No proxies returned from provider.")
                return []

            self.logger.info("Selecting only working proxy...")
            working = await self._validate_fast()
            working.sort(key=lambda p: p.timeout_ms or self.max_timeout)
            self.logger.info(f"{len(working)}/{total_proxies} proxies actually work")
            return working

        except Exception as e:
            self.logger.error(f"Error fetching proxies: {e}.")
            return []

    async def get_proxies(self, internal_call=False):
        """Fetch proxies from the provider (or the fallback one) and set up rotation."""
        self.proxies = await self._fetch_working(self.provider)
        if not self.proxies and self.fallback_provider is not None:
            self.logger.warning("No working proxy from the main provider, trying the fallback one...")
            self.proxies = await self._fetch_working(self.fallback_provider)
        if not self.proxies:
            self.logger.warning("No working proxy. Running without proxies.")

        # Update rotator with current proxies
        self.rotator = ProxyRotator(self.proxies)
        
        # Set initial proxy
        if self.proxies:
            self.current_proxy = self.proxies[0]
            self.current_index = 0
        else:
            self.current_proxy = None
            self.current_index = 0
    
    async def rotate(self):
        """Move to the next proxy in rotation."""
        async with self.lock:
            if self.current_proxy is not None and self.current_proxy in self.proxies:
                self.rotator.remove_proxy(self.current_proxy)

            next_proxy = self.rotator.get_next()
            
            if next_proxy is not None:
                self.current_proxy = next_proxy
                logger.debug(f"Rotated to next proxy: {self.current_proxy}")
            else:
                # No more proxies, try to refresh
                logger.warning("No more proxies available. Attempting to refresh...")
                await self.get_proxies(internal_call=True)
                
                # After refresh, check again
                if self.proxies:
                    self.current_proxy = self.proxies[0]
                    self.rotator = ProxyRotator(self.proxies)
                    self.current_index = 0
                else:
                    logger.warning("Still no proxies available. current_proxy set to None.")
                    self.current_proxy = None
                    self.current_index = 0
    
    async def close(self):
        """Close the providers."""
        await self.provider.close()
        if self.fallback_provider is not None:
            await self.fallback_provider.close()
