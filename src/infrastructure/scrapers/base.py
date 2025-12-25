from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
import logging
from playwright.async_api import BrowserContext, Page
from src.scrapers.base import ScrapedOffer

# Configure Logger
logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """
    Abstract Base Class for all scrapers in the 'El Oráculo de Eternia' architecture.
    Enforces a consistent interface (run, extract) and return type (ScrapedOffer).
    """

    def __init__(self, name: str, base_url: str):
        self.spider_name = name
        self.base_url = base_url
        self.items_scraped = 0
        self.errors = 0

    @abstractmethod
    async def run(self, context: BrowserContext) -> List[ScrapedOffer]:
        """
        Main entry point for the scraper.
        Must return a list of ScrapedOffer objects.
        """
        pass

    async def _safe_navigate(self, page: Page, url: str) -> bool:
        """
        Helper for robust navigation with error handling and human-like delays.
        """
        import random
        import asyncio
        delay = random.uniform(2.0, 5.0)
        logger.info(f"[{self.spider_name}] Humanized delay: {delay:.2f}s before navigating...")
        await asyncio.sleep(delay)
        
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await self._handle_popups(page)
            return True
        except Exception as e:
            logger.error(f"[{self.spider_name}] Error navigating to {url}: {e}")
            self.errors += 1
            return False

    async def _handle_popups(self, page: Page):
        """
        Hook for closing newsletters, cookie banners, etc.
        To be overridden by child classes if needed.
        """
        pass

    def _normalize_price(self, price_raw: float | str) -> float:
        """
        Helper to ensure price is always a float.
        """
        if isinstance(price_raw, (int, float)):
            return float(price_raw)
        if isinstance(price_raw, str):
            try:
                # Basic cleaning: remove currency, replace comma with dot
                # Remove spaces (including non-breaking) to avoid float conversion errors
                clean = price_raw.lower().replace("€", "").replace("eur", "").replace("\xa0", "").strip()
                clean = clean.replace(" ", "")
                clean = clean.replace(".", "").replace(",", ".") # European format: 1.000,00 -> 1000.00
                return float(clean)
            except ValueError:
                logger.warning(f"[{self.spider_name}] Could not normalize price: {price_raw}")
                return 0.0
        return 0.0
