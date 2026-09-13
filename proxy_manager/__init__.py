"""
Proxy Manager Module.

This module provides a clean, pluggable architecture for managing proxies.

## Architecture (Strategy Pattern)

Client Code
    ↓ uses
BaseProxyManager (abstraction)
    ↓ uses
BaseProxyProvider (interface)
    ↓ implemented by
    ├── DefaultProxyProvider (fallback, returns empty)
    ├── RedScrapeProxyProvider (RedScrape API)
    └── YourCustomProvider (future)

## Quick Start

### 1. Basic usage (no proxy)
```python
from proxy_manager import ZoubiProxy, IndustrialProxy, DefaultProxyProvider

# Simple manager
proxy_manager = ZoubiProxy(protocol="http")
await proxy_manager.get_proxies()

# Advanced manager with fallback
proxy_manager = IndustrialProxy(
    countries=["US", "FR"],
    proxy_provider=DefaultProxyProvider()
)
```

### 2. With RedScrape (default)
```python
from proxy_manager import IndustrialProxy

proxy_manager = IndustrialProxy(
    countries=["US", "FR", "DE"],
    protocol="socks5"
)
# Uses RedScrapeProxyProvider by default
```

### 3. Add a new provider
```python
from proxy_manager.providers import BaseProxyProvider

class MyProvider(BaseProxyProvider):
    async def get_proxies(self, filters=None):
        # Your implementation
        return ProxyResponse(proxies=[], total_count=0)
    
    async def get_proxies_by_country(self, country_code, filters=None):
        return await self.get_proxies(filters)
    
    async def close(self):
        pass

# Use it
proxy_manager = IndustrialProxy(
    proxy_provider=MyProvider()
)
```

See PLUGIN_GUIDE.md for detailed instructions.
"""

# Re-export everything for convenience

# Managers
from .managers import ZoubiProxy, IndustrialProxy

# Providers (including base classes and data classes)
from .providers import (
    BaseProxyProvider,
    DefaultProxyProvider,
    RedScrapeProxyProvider,
    ProxyData,
    ProxyFilter,
    ProxyResponse,
)

# Utilities
from .utils import ProxyValidator, ProxyRotator, ProxyFormatter

# Keep backward compatibility
IndustrialZoubiProxy = IndustrialProxy

__all__ = [
    # Managers
    "ZoubiProxy",
    "IndustrialProxy",
    "IndustrialZoubiProxy",  # Backward compatibility
    # Providers
    "BaseProxyProvider",
    "DefaultProxyProvider",
    "RedScrapeProxyProvider",
    # Data Classes
    "ProxyData",
    "ProxyFilter",
    "ProxyResponse",
    # Utilities
    "ProxyValidator",
    "ProxyRotator",
    "ProxyFormatter",
]
