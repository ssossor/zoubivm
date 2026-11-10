"""RootMe API client with proxy support."""

import httpx
import asyncio
import logging
import json
import os
from typing import List, Optional

from proxy_manager import IndustrialProxy, DefaultProxyProvider
from .utils import RootMeApiError, RootMeRateLimitError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class RootMeClient:
    """
    RootMe API client with optional proxy support and API key rotation.
    
    This client allows you to interact with the RootMe API and website
    with or without proxies. If proxies are not available, it falls back
    to direct connections. API keys can be rotated automatically when
    rate limits (HTTP 429) are encountered.
    
    Usage:
        # Load keys from JSON file
        client = await RootMeClient.create_from_file()
        
        # With list of API keys
        client = await RootMeClient.create(
            api_keys=["key1", "key2", "key3"]
        )
        
        # With custom provider
        from proxy_manager.providers import RedScrapeProxyProvider
        client = await RootMeClient.create(
            api_keys=["key1", "key2"],
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
    DEFAULT_API_KEYS_FILE = "rootme_api_keys.json"

    @staticmethod
    def load_api_keys_from_file(file_path: Optional[str] = None) -> List[str]:
        """
        Load API keys from a JSON file.
        
        Args:
            file_path: Path to JSON file. If None, uses DEFAULT_API_KEYS_FILE
            
        Returns:
            List of API keys
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        path = file_path or RootMeClient.DEFAULT_API_KEYS_FILE
        if not os.path.exists(path):
            raise FileNotFoundError(f"API keys file not found: {path}")
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            raise ValueError(f"API keys file must contain a list, got {type(data)}")
        
        return data

    @classmethod
    async def create_from_file(cls, file_path: Optional[str] = None, proxy_provider=None):
        """
        Create a RootMeClient from a JSON file containing API keys.
        
        Args:
            file_path: Path to JSON file with API keys
            proxy_provider: Optional proxy provider
            
        Returns:
            Initialized RootMeClient instance
        """
        api_keys = cls.load_api_keys_from_file(file_path)
        return await cls.create(api_keys, proxy_provider)

    def __init__(self, api_keys: List[str], proxy_provider=None):
        """
        Initialize RootMeClient.
        
        Args:
            api_keys: List of RootMe API keys for rotation
            proxy_provider: Optional proxy provider implementation
                           If None, uses DefaultProxyProvider (no proxies)
        """
        if not isinstance(api_keys, list) or len(api_keys) == 0:
            raise ValueError("api_keys must be a non-empty list of strings")
        
        self.api_keys = api_keys
        self.current_key_index = 0
        self.cookies = {"api_key": self._get_current_api_key()}
        
        # Set up proxy manager
        self.proxy_manager = IndustrialProxy(
            countries=["GB", "DE", "FR", "CA", "ES", "IT", "BE", "CH", "LU", "NL", "PT"],
            protocol="socks5",
            max_timeout=250,
            proxy_provider=proxy_provider or DefaultProxyProvider()
        )
        
        self.client = None
        self.lock = asyncio.Lock()
        self.key_lock = asyncio.Lock()

    @classmethod
    async def create(cls, api_keys: List[str], proxy_provider=None):
        """
        Create and initialize a RootMeClient instance.
        
        Args:
            api_keys: List of RootMe API keys
            proxy_provider: Optional proxy provider
            
        Returns:
            Initialized RootMeClient instance
            
        Raises:
            None - Works without proxies if none are available
        """
        self = cls(api_keys, proxy_provider)
        
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
        logger.info(f"API Keys available: {len(self.api_keys)}")

    def _get_current_api_key(self) -> str:
        """Get the current API key based on index."""
        return self.api_keys[self.current_key_index]

    async def rotate_api_key(self, reason: str = "Unknown"):
        """
        Rotate to the next API key.
        
        Args:
            reason: Reason for rotation (for logging)
        """
        async with self.key_lock:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            new_key = self._get_current_api_key()
            self.cookies = {"api_key": new_key}
            
            # Reinitialize HTTP client with new API key
            await self._init_http_client()
            
            logger.warning(f"Rotated API key ({self.current_key_index}/{len(self.api_keys)}) for: {reason}")

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
            RootMeRateLimitError: If still rate limited after MAX_RETRIES attempts
        """
        for attempt in range(self.MAX_RETRIES):
            response = await self.client.request(method, endpoint, **kwargs)
            if response.status_code != 429:
                return response

            if len(self.api_keys) > 1:
                await self.rotate_api_key("Rate limit (429)")
            await asyncio.sleep(5 * 2 ** attempt)

        raise RootMeRateLimitError("Rate limit exceeded")

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

    async def get_user_id(self, profile_id: str) -> Optional[str]:
        """
        Get user ID from a profile name, as found in the profile URL.

        Args:
            profile_id: Profile name (e.g. "Ssor" or "Aube-643003")

        Returns:
            User ID as string or None if not found
        """
        name, _, suffix = profile_id.rpartition("-")
        if name and suffix.isnumeric():
            return suffix

        try:
            authors = await self.get_authors_from_username({"nom": profile_id})
        except RootMeApiError:
            return None

        for author in authors[0].values() if authors else []:
            if author["nom"] == profile_id:
                return author["id_auteur"]
        return None

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
