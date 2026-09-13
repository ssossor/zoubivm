"""
Proxy Providers (Strategy Pattern).

This module provides a pluggable architecture for proxy sources.
Each provider implements the BaseProxyProvider interface.

Available providers:
- DefaultProxyProvider: Fallback provider (returns empty list)
- RedScrapeProxyProvider: Provider for RedScrape API

To add a new provider:
1. Create a new file in this directory
2. Inherit from BaseProxyProvider
3. Implement get_proxies(), get_proxies_by_country(), and close()
4. Add it to this __init__.py
"""

from .base import (
    BaseProxyProvider,
    ProxyData,
    ProxyFilter,
    ProxyResponse,
)
from .default import DefaultProxyProvider
from .redscrape import RedScrapeProxyProvider

__all__ = [
    # Base interface and data classes
    "BaseProxyProvider",
    "ProxyData",
    "ProxyFilter",
    "ProxyResponse",
    # Concrete implementations
    "DefaultProxyProvider",
    "RedScrapeProxyProvider",
]
