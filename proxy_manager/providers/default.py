"""Default proxy provider - returns empty list (fallback)."""

import logging
from typing import List, Optional, Union

from .base import BaseProxyProvider, ProxyFilter, ProxyResponse, ProxyData

logger = logging.getLogger("proxy_manager.default_provider")


class DefaultProxyProvider(BaseProxyProvider):
    """
    Default proxy provider that always returns an empty list.
    This is used as a fallback when no proxy provider is configured.
    
    This ensures that the system continues to work even without proxies,
    just without using any proxy.
    """
    
    def __init__(self):
        logger.info("DefaultProxyProvider initialized - will return empty proxy list")
    
    async def get_proxies(
        self, 
        filters: Optional[Union[ProxyFilter, dict]] = None
    ) -> ProxyResponse:
        """Always returns an empty ProxyResponse."""
        logger.debug("DefaultProxyProvider.get_proxies() called - returning empty list")
        return ProxyResponse(
            proxies=[],
            total_count=0,
            filters_applied=filters.to_params() if isinstance(filters, ProxyFilter) else filters
        )
    
    async def get_proxies_by_country(
        self,
        country_code: str,
        filters: Optional[Union[ProxyFilter, dict]] = None
    ) -> ProxyResponse:
        """Always returns an empty ProxyResponse for the specified country."""
        logger.debug(f"DefaultProxyProvider.get_proxies_by_country('{country_code}') called - returning empty list")
        return ProxyResponse(
            proxies=[],
            total_count=0,
            filters_applied=filters.to_params() if isinstance(filters, ProxyFilter) else filters
        )
    
    async def close(self):
        """No resources to close."""
        logger.debug("DefaultProxyProvider.close() called")
        pass
