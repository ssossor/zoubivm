"""
Proxy Providers (Strategy Pattern).

This module provides a pluggable architecture for proxy sources.
Each provider implements the BaseProxyProvider interface.

Available providers:
- DefaultProxyProvider: Fallback provider (returns empty list)
- RedScrapeProxyProvider: Provider for RedScrape API
- GeonodeProxyProvider: Provider for the Geonode free proxy list
- ProxyScrapeProxyProvider: Provider for the ProxyScrape free proxy list
- TorProxyProvider: Provider for a Tor SOCKS proxy (one circuit per proxy)
- StormsiaProxyProvider: Provider for the stormsia free proxy list
- ProxiflyProxyProvider: Provider for the Proxifly free proxy list

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
    filter_params,
    wanted_protocols,
)
from .default import DefaultProxyProvider
from .redscrape import RedScrapeProxyProvider
from .geonode import GeonodeProxyProvider
from .proxyscrape import ProxyScrapeProxyProvider
from .tor import TorProxyProvider
from .stormsia import StormsiaProxyProvider
from .proxifly import ProxiflyProxyProvider

__all__ = [
    # Base interface and data classes
    "BaseProxyProvider",
    "ProxyData",
    "ProxyFilter",
    "ProxyResponse",
    # Concrete implementations
    "DefaultProxyProvider",
    "RedScrapeProxyProvider",
    "GeonodeProxyProvider",
    "ProxyScrapeProxyProvider",
    "TorProxyProvider",
    "StormsiaProxyProvider",
    "ProxiflyProxyProvider",
]
