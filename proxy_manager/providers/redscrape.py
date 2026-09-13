"""RedScrape proxy provider implementation."""

import asyncio
import logging
import httpx
from typing import List, Optional, Union

from .base import BaseProxyProvider, ProxyFilter, ProxyResponse, ProxyData

logger = logging.getLogger("proxy_manager.redscrape_provider")


class RedScrapeProxyProvider(BaseProxyProvider):
    """
    Proxy provider for RedScrape API (https://free.redscrape.com).
    
    This is a concrete implementation of BaseProxyProvider that fetches
    proxies from the RedScrape free proxy service.
    """
    
    API_URL = "https://free.redscrape.com/api/proxies"
    
    def __init__(self, timeout: int = 30):
        """
        Initialize the RedScrape proxy provider.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=self.timeout)
        logger.info("RedScrapeProxyProvider initialized")
    
    async def get_proxies(
        self, 
        filters: Optional[Union[ProxyFilter, dict]] = None
    ) -> ProxyResponse:
        """
        Fetch proxies from RedScrape API.
        
        Args:
            filters: Filtering options (country, protocol, timeout, etc.)
            
        Returns:
            ProxyResponse containing the proxies from RedScrape
        """
        params = {}
        
        if filters:
            if isinstance(filters, ProxyFilter):
                params = filters.to_params()
            elif isinstance(filters, dict):
                params = filters.copy()
        
        # Ensure format is JSON
        params['format'] = 'json'
        
        try:
            response = await self._client.get(self.API_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            proxies = []
            
            for item in data:
                if not item.get('is_working'):
                    continue
                    
                proxy = ProxyData(
                    address=item.get('address'),
                    port=item.get('port'),
                    protocol=item.get('protocol', 'http'),
                    country=item.get('country'),
                    country_code=item.get('country_code'),
                    timeout_ms=item.get('timeout_ms'),
                    is_working=item.get('is_working', True),
                    last_checked=item.get('last_checked')
                )
                proxies.append(proxy)
            
            logger.info(f"Fetched {len(proxies)} proxies from RedScrape")
            
            return ProxyResponse(
                proxies=proxies,
                total_count=len(proxies),
                filters_applied=params
            )
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching from RedScrape: {e}")
            return ProxyResponse(proxies=[], total_count=0, filters_applied=params)
        except Exception as e:
            logger.error(f"Error fetching from RedScrape: {e}")
            return ProxyResponse(proxies=[], total_count=0, filters_applied=params)
    
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
        # Apply country filter
        if filters:
            if isinstance(filters, ProxyFilter):
                # Create a copy with country set
                country_filter = ProxyFilter(
                    country=country_code,
                    protocol=filters.protocol,
                    max_timeout=filters.max_timeout,
                    min_timeout=filters.min_timeout,
                    limit=filters.limit,
                    working_only=filters.working_only
                )
                return await self.get_proxies(country_filter)
            else:
                # Dict filter
                new_filters = filters.copy()
                new_filters['country'] = country_code
                return await self.get_proxies(new_filters)
        else:
            # No filters, just country
            return await self.get_proxies(ProxyFilter(country=country_code))
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
        logger.debug("RedScrapeProxyProvider closed")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
