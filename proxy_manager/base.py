"""Base class for proxy managers (Template Method Pattern)."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from .providers.base import ProxyData, ProxyFilter
from .utils import ProxyRotator, ProxyValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger("proxy_manager")


class BaseProxyManager(ABC):
    """
    Abstract base class for proxy managers.
    
    This class provides the common interface and behavior for all proxy managers.
    Concrete implementations should inherit from this and implement the abstract methods.
    """
    
    def __init__(self):
        """Initialize the proxy manager."""
        self.lock = asyncio.Lock()
        self.proxies: List[ProxyData] = []
        self.current_proxy: Optional[ProxyData] = None
        self.logger = logging.getLogger(f"proxy_manager.{self.__class__.__name__}")
        
        # Utilities (can be overridden by implementations)
        self.rotator: ProxyRotator = ProxyRotator(self.proxies)
        self.validator: ProxyValidator = ProxyValidator(timeout=10)
    
    @abstractmethod
    async def get_proxies(self):
        """
        Fetch a new list of proxies and set the current_proxy.
        This should populate self.proxies.
        """
        pass
    
    @abstractmethod
    async def rotate(self):
        """Move to the next proxy in the list."""
        pass
    
    def get_current_proxy(self) -> Optional[ProxyData]:
        """Return the currently used proxy."""
        return self.current_proxy
    
    async def validate_and_filter_proxies(self, max_concurrent: int = 20) -> List[ProxyData]:
        """
        Validate the current proxy list and return only working ones.
        
        Args:
            max_concurrent: Maximum number of concurrent validation requests
            
        Returns:
            List of working ProxyData objects
        """
        if not self.proxies:
            self.logger.warning("No proxies to validate")
            return []
        
        self.logger.info(f"Validating {len(self.proxies)} proxies...")
        working = await self.validator.validate_proxies(self.proxies, max_concurrent)
        self.logger.info(f"{len(working)}/{len(self.proxies)} proxies are working")
        return working
