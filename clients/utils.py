"""Client utilities (headless browser, parsing, etc.)."""

import asyncio
import re
import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


async def scrape_user_id_from_profile(headless_browser, profile_id: str, screenshot_path: str = None):
    """
    Scrap user id from headless browser.
    
    Args:
        headless_browser: Playwright browser instance
        profile_id: Profile ID to scrape
        screenshot_path: Optional path for debug screenshot
        
    Returns:
        User ID as string or None if not found
    """
    user_id = None
    
    page = await headless_browser.new_page()
    
    try:
        await page.goto(f"https://www.root-me.org/{profile_id}")
        await asyncio.sleep(random.uniform(1.5, 2))
        
        if screenshot_path:
            await page.screenshot(path=screenshot_path)
        
        page_content = await page.content()
        soup = BeautifulSoup(page_content, 'lxml')
        div = soup.find('div', class_=re.compile("notation-auteur"))
        
        if div:
            classes = div.get('class')
            target_class = next(
                (c for c in classes if "notation-auteur" in c), None
            )
            
            if target_class:
                match = re.search(r'auteur(\d+)-', target_class)
                if match:
                    user_id = match.group(1)
                    logger.debug(f"ID trouvé : {user_id}")
    finally:
        await page.close()
    
    return user_id


async def scrape_user_points_from_profile(headless_page, profile_id: str, screenshot_path: str = None):
    """
    Scrap user points from headless browser.
    
    Args:
        headless_page: Playwright page instance
        profile_id: Profile ID to scrape
        screenshot_path: Optional path for debug screenshot
        
    Returns:
        Points as string or None if not found
        
    Raises:
        Exception: If page throws an error
    """
    try:
        response = await headless_page.goto(
            f"https://www.root-me.org/{profile_id}",
            timeout=20000,
        )
        
        await asyncio.sleep(random.uniform(1.5, 2))
        
        if screenshot_path:
            await headless_page.screenshot(path=screenshot_path)
        
        page_content = await headless_page.content()
        soup = BeautifulSoup(page_content, 'lxml')
        
        points = None
        for span in soup.find_all('span', {'class': 'gras'}):
            if "Points" in span.text:
                h3_tag = span.find_previous('h3')
                if h3_tag:
                    points = h3_tag.get_text(strip=True)
        
        return points
    except Exception as e:
        raise e


class RootMeRateLimitError(Exception):
    """Exception levée quand le site web ou l'API nous bloque"""
    pass


class RootMeApiError(Exception):
    def __init__(self, message, data):
        super().__init__(message)
        self.data = data
