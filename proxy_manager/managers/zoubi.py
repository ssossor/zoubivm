"""Simple proxy manager using RedScrape API directly."""

import httpx
import asyncio
import logging
import random

from ..base import BaseProxyManager
from ..providers.base import ProxyData, ProxyFilter

logger = logging.getLogger("proxy_manager.ZoubiProxy")


class ZoubiProxy(BaseProxyManager):
    """
    Simple proxy manager that fetches proxies directly from RedScrape API.
    
    This implementation:
    - Uses a single API call to fetch proxies
    - Filters by is_working flag
    - Shuffles the list for random rotation
    - Gracefully handles the case when no proxies are available
    """
    
    API_URL = "https://free.redscrape.com/api/proxies"
    
    def __init__(self, countries=None, protocol="http", max_timeout=500):
        """
        Initialize ZoubiProxy.
        
        Args:
            countries: List of country codes to filter (currently not working in API)
            protocol: Proxy protocol (http, socks5, etc.)
            max_timeout: Maximum timeout in milliseconds
        """
        super().__init__()
        
        self.countries = countries
        self.protocol = protocol
        self.max_timeout = max_timeout
        self.current_index = 0
    
    async def _fetch_proxies(self) -> bool:
        """
        Fetch proxies from RedScrape API.
        
        Returns:
            True if proxies were fetched successfully, False otherwise
        """
        params = {
            "protocol": self.protocol,
            "max_timeout": self.max_timeout,
            "format": "json"
        }
        
        # Note: self.countries doesn't work with RedScrape API currently
        # The API doesn't accept multiple countries in a single request properly
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(self.API_URL, params=params)
                response.raise_for_status()

                data = response.json()
                new_proxies = []
                
                for item in data:
                    if not item.get("is_working"):
                        continue
                    
                    proxy = ProxyData(
                        address=item.get("address"),
                        port=item.get("port"),
                        protocol=item.get("protocol", "http").lower(),
                        country=item.get("country"),
                        country_code=item.get("country_code"),
                        timeout_ms=item.get("timeout_ms"),
                        is_working=item.get("is_working", True)
                    )
                    new_proxies.append(proxy)

                if not new_proxies:
                    self.logger.warning("No proxy found!")
                    return False

                random.shuffle(new_proxies)
                
                self.proxies = new_proxies
                self.current_index = 0
                self.current_proxy = self.proxies[self.current_index] if self.proxies else None
                
                self.logger.info(f"Fetched {len(self.proxies)} new proxies from RedScrape")
                return True

        except Exception as e:
            self.logger.error(f"Error fetching RedScrape: {e}")
            return False
    
    async def get_proxies(self):
        """Fetch proxies and set the current proxy."""
        async with self.lock:
            if not self.proxies:
                success = await self._fetch_proxies()
                if not success:
                    self.logger.warning("No proxies available. Running without proxies.")
                    self.current_proxy = None
                    return
            
            # If we already have proxies, we're good
            self.current_proxy = self.proxies[self.current_index] if self.proxies else None
    
    def get_current_proxy(self) -> ProxyData:
        """Get the current proxy."""
        if not self.proxies:
            self.logger.debug("No proxies available, returning None")
            return None
        return self.proxies[self.current_index]
    
    async def rotate(self):
        """Move to the next proxy in the list."""
        async with self.lock:
            self.current_index += 1

            if self.current_index >= len(self.proxies):
                self.logger.info("No more proxy, refreshing...")
                success = await self._fetch_proxies()
                if not success:
                    self.logger.warning("Failed to refresh proxies. No more proxies available.")
                    self.current_proxy = None
            else:
                self.current_proxy = self.proxies[self.current_index]
                self.logger.debug(f"Rotated to next proxy: {self.proxies[self.current_index]}")
