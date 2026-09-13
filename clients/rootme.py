"""RootMe API client with proxy support."""

import httpx
import asyncio
import logging

from playwright.async_api import async_playwright
from proxy_manager import IndustrialProxy, DefaultProxyProvider
from .utils import (
    scrape_user_id_from_profile,
    scrape_user_points_from_profile,
    RootMeApiError,
    RootMeRateLimitError,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class RootMeClient:
    """
    RootMe API client with optional proxy support.
    
    This client allows you to interact with the RootMe API and website
    with or without proxies. If proxies are not available, it falls back
    to direct connections.
    
    Usage:
        # Without proxy (default)
        client = await RootMeClient.create(api_key)
        
        # With custom provider
        from proxy_manager.providers import RedScrapeProxyProvider
        client = await RootMeClient.create(
            api_key,
            proxy_provider=RedScrapeProxyProvider()
        )
        
        # Get challenges
        challenges = await client.get_challs()
        
        # Get specific challenge
        challenge = await client.get_chall_from_id(challenge_id)
    """
    
    URL = "https://api.www.root-me.org"
    BASE_URL = "https://www.root-me.org"
    MAX_RETRIES = 3

    def __init__(self, api_key: str, proxy_provider=None):
        """
        Initialize RootMeClient.
        
        Args:
            api_key: RootMe API key
            proxy_provider: Optional proxy provider implementation
                           If None, uses DefaultProxyProvider (no proxies)
        """
        self.api_key = api_key
        self.cookies = {"api_key": api_key}
        
        # Set up proxy manager
        self.proxy_manager = IndustrialProxy(
            countries=["GB", "DE", "FR", "CA", "ES", "IT", "BE", "CH", "LU", "NL", "PT"],
            protocol="socks5",
            max_timeout=250,
            proxy_provider=proxy_provider or DefaultProxyProvider()
        )
        
        self.client = None
        self.lock = asyncio.Lock()

    @classmethod
    async def create(cls, api_key: str, proxy_provider=None):
        """
        Create and initialize a RootMeClient instance.
        
        Args:
            api_key: RootMe API key
            proxy_provider: Optional proxy provider
            
        Returns:
            Initialized RootMeClient instance
            
        Raises:
            None - Works without proxies if none are available
        """
        self = cls(api_key, proxy_provider)
        
        # Initialize proxies
        await self.proxy_manager.get_proxies()
        
        if not self.proxy_manager.get_current_proxy():
            logger.warning("No proxy found! Continuing without proxy.")
        
        await self._init_http_client()
        
        return self

    async def _init_http_client(self):
        """Initialize the HTTP client with the current proxy."""
        proxy = self.proxy_manager.get_current_proxy()
        
        # Close previous client if exists
        if self.client:
            await self.client.aclose()
        
        # Configure proxy or None
        proxy_config = proxy.url if proxy else None
        
        self.client = httpx.AsyncClient(
            base_url=self.URL,
            cookies=self.cookies,
            proxy=proxy_config,
            timeout=10.0
        )
        
        if proxy:
            logger.info(f"RootMe Client initialized with proxy: {proxy}")
        else:
            logger.info("RootMe Client initialized without proxy")
        
        logger.info(f"Proxies available: {len(self.proxy_manager.proxies)}")

    async def close(self):
        """Close the client and its resources."""
        if self.client:
            await self.client.aclose()
        await self.proxy_manager.close()

    async def rotate_proxy(self, reason: str = "Unknown"):
        """
        Rotate to the next proxy.
        
        Args:
            reason: Reason for rotation (for logging)
        """
        async with self.lock:
            logger.warning(f"Rotating proxy for: {reason}")
            await self.proxy_manager.rotate()
            
            old_client = self.client
            await self._init_http_client()
            
            if old_client:
                await old_client.aclose()
            
            await asyncio.sleep(0.5)

    async def request(self, method: str, endpoint: str, **kwargs):
        """
        Make a generic HTTP request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments for httpx
            
        Returns:
            httpx.Response object
            
        Raises:
            RootMeRateLimitError: If rate limited
        """
        response = await self.client.request(method, endpoint, **kwargs)
        
        if response.status_code == 429:
            raise RootMeRateLimitError("Rate limit exceeded")
        
        return response

    async def req_get_api(self, endpoint: str, params=None):
        """
        Make a GET request to the API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            httpx.Response object
        """
        response = await self.request("GET", endpoint, params=params)
        
        if response.status_code >= 400 and response.status_code != 429:
            logger.error(f"API Error {response.status_code}: {endpoint}")
        
        return response

    async def get_user_id_from_headless(self, profile_id: str) -> str:
        """
        Get user ID by scraping the profile page with a headless browser.
        
        Args:
            profile_id: Profile ID to scrape
            
        Returns:
            User ID as string or None if not found
        """
        async with async_playwright() as p:
            browser = await p.firefox.launch()
            try:
                user_id = await scrape_user_id_from_profile(
                    browser,
                    profile_id,
                    screenshot_path='screenshots/debug_register.png'
                )
                return user_id
            finally:
                await browser.close()

    async def get_user_points_headless(self, profile_id: str, page) -> str:
        """
        Get user points by scraping the profile page.
        
        Args:
            profile_id: Profile ID to scrape
            page: Playwright page instance
            
        Returns:
            Points as string or None if not found
            
        Raises:
            RootMeRateLimitError: If rate limited
            Exception: On other errors
        """
        try:
            points = await scrape_user_points_from_profile(
                page,
                profile_id,
                screenshot_path="screenshots/get_user_points.png"
            )
            return points
        except Exception as e:
            error_msg = str(e).lower()
            proxy_errors = [
                "err_proxy_connection_failed",
                "err_connection_reset",
                "err_tunnel_connection_failed",
                "ssl_error",
                "timeout"
            ]
            
            if any(err in error_msg for err in proxy_errors):
                logger.warning(f"Proxy error detected: {e}")
                raise RootMeRateLimitError(f"Proxy Failure: {e}")
            
            raise e

    async def get_challs(self) -> dict:
        """
        Get all challenges.
        
        Returns:
            Dictionary of all challenges
            
        Raises:
            RootMeApiError: If API request fails
        """
        response = await self.req_get_api("/challenges")
        if response.status_code == 200:
            return response.json()
        raise RootMeApiError("Can't get all challenges", response)

    async def get_chall_from_id(self, challenge_id: str) -> dict:
        """
        Get a specific challenge by ID.
        
        Args:
            challenge_id: Challenge ID
            
        Returns:
            Challenge data as dictionary
            
        Raises:
            RootMeApiError: If API request fails
        """
        response = await self.req_get_api(f"/challenges/{str(challenge_id)}")
        if response.status_code == 200:
            return response.json()
        raise RootMeApiError(f"Can't get challenge {challenge_id}", response)

    async def get_authors_from_username(self, params: dict) -> list:
        """
        Get authors from username.
        
        Args:
            params: Query parameters
            
        Returns:
            List of authors
            
        Raises:
            RootMeApiError: If API request fails
        """
        response = await self.req_get_api("/auteurs", params=params)
        if response.status_code == 200:
            return response.json()
        raise RootMeApiError("Can't get authors from username", response)

    async def get_author_from_id(self, author_id: str) -> dict:
        """
        Get a specific author by ID.
        
        Args:
            author_id: Author ID
            
        Returns:
            Author data as dictionary
            
        Raises:
            RootMeApiError: If API request fails
        """
        response = await self.req_get_api(f"/auteurs/{author_id}")
        if response.status_code == 200:
            return response.json()
        raise RootMeApiError(f"Can't get author with ID {author_id}", response)
