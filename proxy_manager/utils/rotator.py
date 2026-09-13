"""Proxy rotation utilities."""

import logging
from typing import List, Optional

from ..providers.base import ProxyData

logger = logging.getLogger("proxy_manager.utils.rotator")


class ProxyRotator:
    """Utility class for rotating through a list of proxies."""
    
    def __init__(self, proxies: List[ProxyData]):
        """
        Initialize the proxy rotator.
        
        Args:
            proxies: List of ProxyData objects to rotate through
        """
        self.proxies = proxies
        self.current_index = 0
    
    def get_next(self) -> Optional[ProxyData]:
        """
        Get the next proxy in rotation.
        
        Returns:
            Next ProxyData object or None if list is empty
        """
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def get_random(self) -> Optional[ProxyData]:
        """
        Get a random proxy from the list.
        
        Returns:
            Random ProxyData object or None if list is empty
        """
        if not self.proxies:
            return None
        
        import random
        return random.choice(self.proxies)
    
    def remove_proxy(self, proxy: ProxyData) -> bool:
        """
        Remove a proxy from the rotation list.
        
        Args:
            proxy: ProxyData object to remove
            
        Returns:
            True if proxy was removed, False if not found
        """
        try:
            index = self.proxies.index(proxy)
            self.proxies.pop(index)
            
            # Adjust current index if necessary
            if index <= self.current_index and self.current_index > 0:
                self.current_index -= 1
            
            # Reset index if we're at the end
            if self.current_index >= len(self.proxies) and self.proxies:
                self.current_index = 0
            
            return True
        except ValueError:
            return False
    
    def add_proxy(self, proxy: ProxyData):
        """
        Add a proxy to the rotation list.
        
        Args:
            proxy: ProxyData object to add
        """
        self.proxies.append(proxy)
    
    def size(self) -> int:
        """Get the number of proxies in rotation."""
        return len(self.proxies)
    
    def is_empty(self) -> bool:
        """Check if the rotation list is empty."""
        return len(self.proxies) == 0
