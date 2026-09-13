"""Proxy formatting utilities."""

from typing import List, Dict

from ..providers.base import ProxyData


class ProxyFormatter:
    """Utility class for formatting proxy data."""
    
    @staticmethod
    def to_curl_format(proxies: List[ProxyData]) -> List[str]:
        """
        Format proxies for use with curl.
        
        Args:
            proxies: List of ProxyData objects
            
        Returns:
            List of curl proxy strings
        """
        return [f"--proxy {proxy.url}" for proxy in proxies]
    
    @staticmethod
    def to_requests_format(proxies: List[ProxyData]) -> List[Dict[str, str]]:
        """
        Format proxies for use with requests library.
        
        Args:
            proxies: List of ProxyData objects
            
        Returns:
            List of proxy dictionaries for requests
        """
        return [proxy.to_dict() for proxy in proxies]
    
    @staticmethod
    def to_simple_list(proxies: List[ProxyData]) -> List[str]:
        """
        Format proxies as simple address:port strings.
        
        Args:
            proxies: List of ProxyData objects
            
        Returns:
            List of address:port strings
        """
        return [f"{proxy.address}:{proxy.port}" for proxy in proxies]
