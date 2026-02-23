import httpx
import asyncio
import re
import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
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


class RootMeClient:
    URL = "https://api.www.root-me.org"
    BASE_URL = "https://www.root-me.org"

    def __init__(self, api_key):
        self.cookies = {"api_key": api_key}
        self.client = httpx.AsyncClient(
            base_url=self.URL, cookies=self.cookies)
        logger.info("Root Me Client initialized!")

    async def close(self):
        """Ferme la session HTTP"""
        await self.client.aclose()

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

    async def get_user_points_headless(self, profile_id, browser, page):
        """
        Scrap user points from headless browser
        """
        points = None
        await page.goto(f"{self.BASE_URL}/{profile_id}")
        await asyncio.sleep(random.uniform(1.5, 2))

        page_content = await page.content()
        soup = BeautifulSoup(page_content, 'lxml')

        for span in soup.find_all('span', {'class': 'gras'}):
            if "Points" in span.text:
                h3_tag = span.find_previous('h3')
                if h3_tag:
                    points = h3_tag.get_text(strip=True)
                    logger.debug(f"{profile_id}: {points}pts")
        return points

    async def req_get_api(self, endpoint: str, params=None):
        """
        Effectue une requête GET asynchrone sur l'API
        """
        try:
            response = await self.client.get(endpoint, params=params)
            return response
        except httpx.RequestError as err:
            logger.error(f"Erreur réseau vers l'API : {err}")
            raise

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
