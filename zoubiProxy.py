import httpx
import asyncio
import logging
import random

logger = logging.getLogger("ProxyManager")


class Proxy:
    def __init__(self, data: dict):
        self.address = data.get("address")
        self.port = data.get("port")
        self.protocol = data.get("protocol", "http").lower()
        self.country = data.get("country")
        self.country_code = data.get("country_code")
        self.timeout_ms = data.get("timeout_ms")
        self.is_working = data.get("is_working", True)

    def as_string(self) -> str:
        prefix = "socks5" if "socks5" in self.protocol else "http"
        return f"{prefix}://{self.address}:{self.port}"

    def __repr__(self):
        return f"<Proxy {self.as_string()} ({self.country_code})>"


class ZoubiProxy:
    API_URL = "https://free.redscrape.com/api/proxies"

    def __init__(self, country=None, protocol="http", max_timeout=500):
        self.country = country
        self.protocol = protocol
        self.max_timeout = max_timeout

        self.proxies = []
        self.current_index = 0
        self.lock = asyncio.Lock()

    async def _fetch_proxies(self):
        params = {
            "protocol": self.protocol,
            "max_timeout": self.max_timeout,
            "format": "json"
        }

        if self.country:
            params["country"] = ",".join(self.country)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(self.API_URL, params=params)
                response.raise_for_status()

                data = response.json()
                new_proxies = [Proxy(p) for p in data if p.get("is_working")]

                if not new_proxies:
                    logger.warning("No proxy found!")
                    return False

                random.shuffle(new_proxies)

                self.proxies = new_proxies
                self.current_index = 0
                logger.info(f"Fetched {len(self.proxies)
                                       } new proxies from RedScrape")
                return True

        except Exception as e:
            logger.error(f"Error fetching RedScrape : {e}")
            return False

    async def get(self) -> Proxy:
        async with self.lock:
            if not self.proxies:
                success = await self._fetch_proxies()
                if not success:
                    return None

            return self.proxies[self.current_index]

    async def rotate(self):
        async with self.lock:
            self.current_index += 1

            if self.current_index >= len(self.proxies):
                logger.info("No more proxy, refreshing...")
                await self._fetch_proxies()
            else:
                logger.debug(f"Rotated to next proxy: {
                             self.proxies[self.current_index]}")
