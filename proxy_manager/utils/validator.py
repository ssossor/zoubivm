"""Proxy validation utilities."""

import asyncio
import logging
from typing import List, Optional
import aiohttp
from aiohttp_socks import ProxyConnector

from ..providers.base import ProxyData

logger = logging.getLogger("proxy_manager.utils.validator")


class ProxyValidator:
    """Utility class for validating proxy functionality."""
    
    def __init__(self, timeout: int = 10, test_url: str = "https://httpbin.org/ip"):
        """
        Initialize the proxy validator.
        
        Args:
            timeout: Timeout for validation requests in seconds
            test_url: URL to use for testing proxy functionality
        """
        self.timeout = timeout
        self.test_url = test_url
    
    async def validate_proxy(
        self, 
        proxy: ProxyData, 
        session: Optional[aiohttp.ClientSession] = None
    ) -> bool:
        """
        Validate a single proxy by making a test request.
        
        Args:
            proxy: ProxyData object to validate
            session: Optional aiohttp session to use
            
        Returns:
            True if proxy is working, False otherwise
        """
        is_socks = proxy.protocol.lower().startswith('socks')
        
        try:
            if is_socks:
                connector = ProxyConnector.from_url(proxy.url)
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as socks_session:
                    async with socks_session.get(self.test_url) as response:
                        return response.status == 200
            else:
                close_session = False
                if session is None:
                    session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
                    close_session = True
                
                try:
                    async with session.get(self.test_url, proxy=proxy.url) as response:
                        return response.status == 200
                finally:
                    if close_session:
                        await session.close()
        except Exception as e:
            logger.debug(f"Proxy {proxy} failed validation: {e}")
            return False
    
    async def validate_proxies(
        self, 
        proxies: List[ProxyData], 
        max_concurrent: int = 20
    ) -> List[ProxyData]:
        """
        Validate a list of proxies asynchronously.
        
        Args:
            proxies: List of ProxyData objects to validate
            max_concurrent: Maximum number of concurrent validation requests
            
        Returns:
            List of working ProxyData objects
        """
        if not proxies:
            return []
            
        semaphore = asyncio.Semaphore(max_concurrent)
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as http_session:
            
            async def validate_with_semaphore(proxy: ProxyData) -> Optional[ProxyData]:
                async with semaphore:
                    is_working = await self.validate_proxy(proxy, http_session)
                    return proxy if is_working else None
            
            tasks = [validate_with_semaphore(proxy) for proxy in proxies]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            return [res for res in results if isinstance(res, ProxyData)]
