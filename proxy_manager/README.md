# Proxy Manager

> A clean, pluggable architecture for proxy management with support for multiple providers.

## 🎯 Architecture

This module uses the **Strategy Pattern** to provide a flexible way to integrate different proxy providers:

```
Client Code (clients/rootme.py)
    ↓ uses
Proxy Manager (ZoubiProxy or IndustrialProxy)
    ↓ uses
Proxy Provider (BaseProxyProvider interface)
    ↓ implemented by
    ├── DefaultProxyProvider → returns empty list (fallback)
    ├── RedScrapeProxyProvider → RedScrape API
    ├── GeonodeProxyProvider → Geonode free proxy list (used by the bot)
    ├── ProxyScrapeProxyProvider → ProxyScrape free proxy list (bot fallback)
    ├── TorProxyProvider → Tor SOCKS proxy, one circuit per proxy (used first by the bot)
    ├── StormsiaProxyProvider → stormsia free proxy list (bot fallback)
    ├── ProxiflyProxyProvider → Proxifly free proxy list (bot fallback)
    └── YourCustomProvider → your implementation
```

## 📦 Installation

This module is part of the zoubivm project and doesn't require separate installation.

## 🚀 Quick Start

### 1. No Proxy (Fallback Mode)

```python
from proxy_manager import ZoubiProxy, IndustrialProxy, DefaultProxyProvider

# Simple usage
proxy_manager = ZoubiProxy(protocol="http")
await proxy_manager.get_proxies()  # Works without actual proxies

# Or with explicit fallback
proxy_manager = IndustrialProxy(
    countries=["US", "FR"],
    proxy_provider=DefaultProxyProvider()
)
```

### 2. With RedScrape (Default)

```python
from proxy_manager import IndustrialProxy

# Uses RedScrapeProxyProvider by default
proxy_manager = IndustrialProxy(
    countries=["US", "FR", "DE"],
    protocol="socks5",
    max_timeout=250
)
await proxy_manager.get_proxies()
```

### 3. Add a Custom Provider

Create a new file in `proxy_manager/providers/`:

```python
# proxy_manager/providers/my_provider.py
from typing import List, Optional, Union
from .base import BaseProxyProvider, ProxyData, ProxyFilter, ProxyResponse


class MyProxyProvider(BaseProxyProvider):
    """Custom proxy provider for your API."""
    
    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://your-proxy-api.com"
    
    async def get_proxies(self, filters: Optional[Union[ProxyFilter, dict]] = None) -> ProxyResponse:
        """Fetch all proxies from your API."""
        # Your implementation here
        proxies = []  # List of ProxyData objects
        return ProxyResponse(
            proxies=proxies,
            total_count=len(proxies),
            filters_applied=filters.to_params() if isinstance(filters, ProxyFilter) else filters
        )
    
    async def get_proxies_by_country(self, country_code: str, filters: Optional[Union[ProxyFilter, dict]] = None) -> ProxyResponse:
        """Fetch proxies for a specific country."""
        # Implement country-specific fetching
        return await self.get_proxies(filters)
    
    async def close(self):
        """Close any open resources."""
        pass
```

Then use it:

```python
from proxy_manager import IndustrialProxy
from proxy_manager.providers.my_provider import MyProxyProvider

provider = MyProxyProvider(api_key="your_key")
proxy_manager = IndustrialProxy(
    countries=["US", "FR"],
    proxy_provider=provider
)
```

## 📚 API Reference

### Proxy Managers

#### ZoubiProxy (Simple)

Simple proxy manager that fetches proxies directly from RedScrape:
- Single API call
- Shuffles proxy list
- No validation (trusts `is_working` flag)

```python
ZoubiProxy(
    countries=None,
    protocol="http",
    max_timeout=500
)
```

#### IndustrialProxy (Advanced)

Advanced proxy manager with:
- Pluggable proxy providers
- Real HTTP validation of proxies
- Multi-country support
- Smart rotation with bad proxy removal

```python
IndustrialProxy(
    countries=None,
    protocol="http",
    max_timeout=500,
    working_only=True,
    limit=30,
    proxy_provider=None,  # Uses RedScrapeProxyProvider if None
    fallback_providers=None,  # Tried in order when proxy_provider gives no working proxy
    test_url="https://httpbin.org/ip"  # URL a proxy must reach to be kept
)
```

### Proxy Providers

All providers implement the `BaseProxyProvider` interface:

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_proxies` | `async get_proxies(filters=None) -> ProxyResponse` | Get all proxies |
| `get_proxies_by_country` | `async get_proxies_by_country(country_code, filters=None) -> ProxyResponse` | Get proxies for country |
| `get_multiple_countries` | `async get_multiple_countries(country_codes, filters=None) -> List[ProxyResponse]` | Get for multiple countries |
| `close` | `async close()` | Close resources |

### Data Classes

#### ProxyData

```python
ProxyData(
    address: str,              # IP address
    port: int,                 # Port number
    protocol: str = "http",    # http, https, socks4, socks5
    country: Optional[str] = None,
    country_code: Optional[str] = None,
    timeout_ms: Optional[int] = None,
    is_working: bool = True,
    last_checked: Optional[datetime] = None
)
```

Properties:
- `url` → `"protocol://address:port"`
- `to_dict()` → `{"http": url, "https": url}` (for requests library)

#### ProxyFilter

```python
ProxyFilter(
    country: Optional[str] = None,
    protocol: Optional[str] = None,
    max_timeout: Optional[int] = None,
    min_timeout: Optional[int] = None,
    limit: Optional[int] = None,
    working_only: bool = True
)
```

Method:
- `to_params()` → Converts to dict for API calls

#### ProxyResponse

```python
ProxyResponse(
    proxies: List[ProxyData],
    total_count: int = 0,
    filters_applied: Optional[dict] = None
)
```

### Utilities

#### ProxyRotator

```python
rotator = ProxyRotator(proxies)
rotator.get_next()      # Get next proxy in rotation
rotator.get_random()    # Get random proxy
rotator.remove_proxy(p) # Remove a proxy
rotator.add_proxy(p)    # Add a proxy
```

#### ProxyValidator

```python
validator = ProxyValidator(timeout=10, test_url="https://httpbin.org/ip")
working = await validator.validate_proxies(proxies, max_concurrent=20)
```

#### ProxyFormatter

```python
formatter = ProxyFormatter()
formatter.to_curl_format(proxies)    # List of --proxy flags
formatter.to_requests_format(proxies) # List of dicts for requests
formatter.to_simple_list(proxies)    # List of "ip:port" strings
```

## 🔧 Integration with RootMeClient

`RootMeClient` (`clients/rootme.py`) starts without proxy and only fetches proxies on
the first rate limit. It asks for SOCKS5 and HTTP(S) proxies (`protocol="socks5,http,https"`)
and the bot uses Tor, then Geonode, stormsia, ProxyScrape and Proxifly:

```python
from clients import RootMeClient
from proxy_manager import (GeonodeProxyProvider, ProxiflyProxyProvider, ProxyScrapeProxyProvider,
                           StormsiaProxyProvider, TorProxyProvider)

client = await RootMeClient.create(
    api_keys=["key1", "key2"],
    proxy_provider=TorProxyProvider("socks5://tor:9050"),
    fallback_proxy_providers=[GeonodeProxyProvider(), StormsiaProxyProvider(),
                              ProxyScrapeProxyProvider(), ProxiflyProxyProvider()]
)
```

A provider reads `filters` with `filter_params()` and the asked protocols, in order of
preference, with `wanted_protocols()`. An "https" proxy is an HTTP proxy that tunnels
HTTPS: `ProxyData.url` gives it an `http://` URL.

`TorProxyProvider` gives each proxy random SOCKS credentials: Tor isolates streams by
credentials, so each proxy gets its own circuit, and every fetch gives new circuits.

## 🎓 Best Practices

1. **Always handle errors** in `get_proxies()` - return empty `ProxyResponse` on failure
2. **Don't block the event loop** - all methods must be async
3. **Close resources** - implement `close()` to clean up connections
4. **Respect the interface** - use `ProxyData`, `ProxyFilter`, `ProxyResponse` classes
5. **Test your provider** - make sure it works before integrating

## 📁 Structure

```
proxy_manager/
├── __init__.py              # Main exports
├── base.py                  # BaseProxyManager
├── managers/
│   ├── __init__.py
│   ├── zoubi.py            # ZoubiProxy
│   └── industrial.py       # IndustrialProxy
├── providers/
│   ├── __init__.py
│   ├── base.py             # BaseProxyProvider + Data Classes
│   ├── default.py          # DefaultProxyProvider
│   ├── redscrape.py        # RedScrapeProxyProvider
│   ├── geonode.py          # GeonodeProxyProvider
│   ├── proxyscrape.py      # ProxyScrapeProxyProvider
│   ├── stormsia.py         # StormsiaProxyProvider
│   ├── proxifly.py         # ProxiflyProxyProvider
│   └── tor.py              # TorProxyProvider
├── utils/
│   ├── __init__.py
│   ├── rotator.py          # ProxyRotator
│   ├── validator.py        # ProxyValidator
│   └── formatter.py        # ProxyFormatter
└── README.md               # This file
```

## 🤝 Contributing

To add a new proxy provider:

1. Create a new file in `proxy_manager/providers/`
2. Inherit from `BaseProxyProvider`
3. Implement the required methods
4. Add it to `providers/__init__.py`
5. Test it thoroughly
6. Create a PR with your changes

## 📄 License

Part of the zoubivm project.
