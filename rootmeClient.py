import httpx
import asyncio
import re
import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from zoubiProxy import ZoubiProxy
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class RootMeApiError(Exception):
    def __init__(self, message, data):
        super().__init__(message)
        self.data = data


class RootMeRateLimitError(Exception):
    """Exception levée quand le site web ou l'API nous bloque"""
    pass


class RootMeClient:
    URL = "https://api.www.root-me.org"
    BASE_URL = "https://www.root-me.org"

    def __init__(self, api_key):
        self.api_key = api_key
        self.cookies = {"api_key": api_key}
        self.proxy_manager = ZoubiProxy(
            protocol="socks5",
            max_timeout=250
        )
        self.client = None
        self.lock = asyncio.Lock()

    @classmethod
    async def create(cls, api_key):
        self = cls(api_key)

        await self.proxy_manager.rotate()
        await self._init_client()

        return self

    async def _init_client(self):
        proxy_obj = await self.proxy_manager.get()
        proxy_str = proxy_obj.as_string() if proxy_obj else None

        if self.client:
            await self.client.aclose()

        self.client = httpx.AsyncClient(
            base_url=self.URL,
            cookies=self.cookies,
            proxy=proxy_str,
            timeout=10.0
        )
        logger.info(f"Root Me Client initialized!\nProxy: {proxy_str}")
        logger.info(f"Proxies available: {self.proxy_manager.proxies}")

    async def rotate_proxy(self, reason="Unknown"):
        """Secure proxy rotation"""
        async with self.lock:
            logger.warning(f"Rotating proxy for : {reason}")
            await self.proxy_manager.rotate()

            old_client = self.client
            await self._init_client()
            if old_client:
                await old_client.aclose()
            await asyncio.sleep(0.5)

    async def request(self, method, endpoint, **kwargs):
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self.client.request(method, endpoint, **kwargs)

                if response.status_code == 429:
                    if attempt < self.MAX_RETRIES - 1:
                        await self._handle_429()
                        continue

                return response

            except (httpx.ProxyError, httpx.ConnectError):
                await self._handle_429()
                continue

        return response

    async def get_user_id_from_headless(self, profile_id: str):
        """
        Scrap user id from headless browser
        """
        user_id = None

        async with async_playwright() as p:
            browser = await p.firefox.launch()
            page = await browser.new_page()

            await page.goto(f"{self.BASE_URL}/{profile_id}")

            await asyncio.sleep(random.uniform(1.5, 2))

            await page.screenshot(path='screenshots/debug_register.png')

            page_content = await page.content()
            soup = BeautifulSoup(page_content, 'lxml')
            div = soup.find('div', class_=re.compile("notation-auteur"))

            if div:
                classes = div.get('class')
                target_class = next(
                    (c for c in classes if "notation-auteur" in c), None)

                if target_class:
                    match = re.search(r'auteur(\d+)-', target_class)
                    if match:
                        user_id = match.group(1)
                        logger.debug(f"ID trouvé : {user_id}")

            await browser.close()
        return user_id

    async def get_user_points_headless(self, profile_id, page):
        try:
            response = await page.goto(
                f"{self.BASE_URL}/{profile_id}",
                timeout=20000,
            )
            if response and response.status == 429:
                raise RootMeRateLimitError("Rate limit hit on Headless")

            await asyncio.sleep(random.uniform(1.5, 2))
            await page.screenshot(path="screenshots/get_user_points.png")
            page_content = await page.content()
            soup = BeautifulSoup(page_content, 'lxml')

            points = None
            for span in soup.find_all('span', {'class': 'gras'}):
                if "Points" in span.text:
                    h3_tag = span.find_previous('h3')
                    if h3_tag:
                        points = h3_tag.get_text(strip=True)
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
                logger.warning(f"Proxy error detected : {e}")
                raise RootMeRateLimitError(f"Proxy Failure: {e}")

            raise e

    async def req_get_api(self, endpoint: str, params=None):
        response = await self.request("GET", endpoint, params=params)

        if response.status_code >= 400 and response.status_code != 429:
            logger.error(f"API Eroor {response.status_code} : {endpoint}")

        return response

    async def get_challs(self) -> dict:
        r = await self.req_get_api("/challenges")
        if r.status_code == 200:
            return r.json()
        raise RootMeApiError("Can't get all challenges", r)

    async def get_chall_from_id(self, challenge_id: str) -> dict:
        r = await self.req_get_api(f"/challenges/{str(challenge_id)}")
        if r.status_code == 200:
            return r.json()
        raise RootMeApiError(f"Can't get challenge {challenge_id}", r)

    async def get_authors_from_username(self, params: dict) -> list:
        r = await self.req_get_api("/auteurs", params=params)
        if r.status_code == 200:
            return r.json()
        raise RootMeApiError("Can't get authors from username", r)

    async def get_author_from_id(self, author_id: str) -> dict:
        r = await self.req_get_api(f"/auteurs/{author_id}")
        if r.status_code == 200:
            return r.json()
        raise RootMeApiError(f"Can't get author with ID {author_id}", r)
