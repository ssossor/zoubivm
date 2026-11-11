"""Base interface for proxy providers (Strategy Pattern)."""

import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote


@dataclass
class ProxyData:
    """Represents a single proxy with all its metadata."""
    address: str
    port: int
    protocol: str = "http"
    country: Optional[str] = None
    country_code: Optional[str] = None
    timeout_ms: Optional[int] = None
    is_working: bool = True
    last_checked: Optional[datetime] = None
    username: Optional[str] = None
    password: Optional[str] = None
    
    @property
    def url(self) -> str:
        """
        Return the proxy URL in the format protocol://[user:password@]address:port.

        An "https" proxy is an HTTP proxy that tunnels HTTPS (CONNECT): it is reached
        with http://.
        """
        prefix = "http" if self.protocol == "https" else self.protocol
        auth = ""
        if self.username:
            auth = f"{quote(self.username, safe='')}:{quote(self.password or '', safe='')}@"
        return f"{prefix}://{auth}{self.address}:{self.port}"
    
    def to_dict(self) -> dict:
        """Return a dictionary representation for requests library."""
        return {
            'http': self.url,
            'https': self.url
        }
    
    def __repr__(self):
        return f"<Proxy {self.protocol}://{self.address}:{self.port} ({self.country_code or 'Unknown'}]>"


@dataclass 
class ProxyFilter:
    """Filter options for proxy requests. `protocol` may list several protocols: "socks5,http"."""
    country: Optional[str] = None
    protocol: Optional[str] = None
    max_timeout: Optional[int] = None
    min_timeout: Optional[int] = None
    limit: Optional[int] = None
    working_only: bool = True
    
    def to_params(self) -> dict:
        """Convert filter to URL parameters."""
        params = {}
        
        if self.country:
            params['country'] = self.country
        if self.protocol:
            params['protocol'] = self.protocol
        if self.max_timeout is not None:
            params['max_timeout'] = self.max_timeout
        if self.min_timeout is not None:
            params['min_timeout'] = self.min_timeout
        if self.limit is not None:
            params['limit'] = self.limit
        if self.working_only:
            params['working_only'] = 'true'
            
        return params


@dataclass
class ProxyResponse:
    """Response from a proxy provider."""
    proxies: List[ProxyData]
    total_count: int = field(default=0)
    filters_applied: Optional[dict] = None
    
    def __len__(self) -> int:
        return len(self.proxies)
    
    def __iter__(self):
        return iter(self.proxies)
    
    def __getitem__(self, index):
        return self.proxies[index]


def filter_params(filters: Optional[Union[ProxyFilter, dict]]) -> dict:
    """
    Return filters as a dict, whether given as a ProxyFilter, a dict or None.

    Args:
        filters: Filtering options

    Returns:
        Filters as a dict (empty if None)
    """
    if isinstance(filters, ProxyFilter):
        return filters.to_params()
    return dict(filters or {})


def wanted_protocols(filters: dict) -> List[str]:
    """
    Return the protocols asked in filters, in order of preference.

    Args:
        filters: Filters as a dict, with "protocol" like "socks5,http,https"

    Returns:
        List of protocols, empty if any protocol is accepted
    """
    return [p for p in filters.get("protocol", "").split(",") if p]


class BaseProxyProvider(ABC):
    """
    Abstract base class for proxy providers (Strategy Pattern).
    
    Any new proxy source should inherit from this class and implement
    the abstract methods.
    """
    
    @abstractmethod
    async def get_proxies(
        self, 
        filters: Optional[Union[ProxyFilter, dict]] = None
    ) -> ProxyResponse:
        """
        Fetch proxies from the provider.
        
        Args:
            filters: Filtering options for the request
            
        Returns:
            ProxyResponse containing the list of proxies
        """
        pass
    
    @abstractmethod
    async def get_proxies_by_country(
        self,
        country_code: str,
        filters: Optional[Union[ProxyFilter, dict]] = None
    ) -> ProxyResponse:
        """
        Fetch proxies from a specific country.
        
        Args:
            country_code: Two-letter country code (e.g., 'US', 'FR')
            filters: Additional filtering options
            
        Returns:
            ProxyResponse containing proxies from the specified country
        """
        pass
    
    async def get_multiple_countries(
        self,
        country_codes: List[str],
        filters: Optional[Union[ProxyFilter, dict]] = None
    ) -> List[ProxyResponse]:
        """
        Fetch proxies from multiple countries concurrently.
        
        Args:
            country_codes: List of two-letter country codes
            filters: Filtering options
            
        Returns:
            List of ProxyResponse objects (one per country)
        """
        # Default implementation: sequential fetch for each country
        tasks = []
        for country in country_codes:
            task = self.get_proxies_by_country(country, filters)
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
    
    @abstractmethod
    async def close(self):
        """Close any open resources (HTTP sessions, connections, etc.)."""
        pass
