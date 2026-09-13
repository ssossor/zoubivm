"""Base interface for proxy providers (Strategy Pattern)."""

import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime


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
    
    @property
    def url(self) -> str:
        """Return the proxy URL in the format protocol://address:port."""
        prefix = "socks5" if self.protocol == "socks5" else self.protocol
        return f"{prefix}://{self.address}:{self.port}"
    
    def to_dict(self) -> dict:
        """Return a dictionary representation for requests library."""
        return {
            'http': self.url,
            'https': self.url
        }
    
    def __repr__(self):
        return f"<Proxy {self.url} ({self.country_code or 'Unknown'}]>"


@dataclass 
class ProxyFilter:
    """Filter options for proxy requests."""
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
