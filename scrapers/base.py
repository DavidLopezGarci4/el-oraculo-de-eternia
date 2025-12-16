import asyncio
import aiohttp
import random
import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass
from models import ProductOffer

# Configuration Constants
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

class AsyncScraperPlugin(ABC):
    """
    Abstract Base Class for Async Scrapers using aiohttp.
    Implements polite scraping patterns: concurrency limits, retries, jitter.
    """
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.session = session # If None, must be set before use or managed internally
        self._semaphore = asyncio.Semaphore(3) # Max 3 concurrent requests per domain
        self.logger = logging.getLogger(f"scraper.{self.name}")

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        pass

    @abstractmethod
    async def search(self, query: str) -> List[ProductOffer]:
        """
        Implementation of the specific search logic.
        Must handle its own pagination and parsing logic.
        """
        pass

    async def fetch(self, url: str, params: dict = None, headers: dict = None, is_json: bool = False):
        """
        Robust fetch with retries, jitter and rate limiting.
        """
        if not headers:
            headers = DEFAULT_HEADERS.copy()
            
        async with self._semaphore:
            # Polite Jitter before request
            await asyncio.sleep(random.uniform(0.5, 1.5)) 
            
            for attempt in range(3):
                try:
                    # Use provided session or create a temporary one (not recommended for prod, but failsafe)
                    if self.session:
                        async with self.session.get(url, params=params, headers=headers, timeout=15) as response:
                            if response.status in [200, 201]:
                                if is_json:
                                    return await response.json()
                                return await response.text()
                            elif response.status in [429, 503]:
                                wait_time = (2 ** attempt) + random.uniform(0, 1)
                                self.logger.warning(f"[{self.name}] Rate limit {response.status}. Waiting {wait_time:.2f}s...")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                self.logger.error(f"[{self.name}] Failed {url} with status {response.status}")
                                return None
                    else:
                        raise RuntimeError("Session not initialized")

                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                     self.logger.warning(f"[{self.name}] Network error attempt {attempt+1}: {str(e)}")
                     await asyncio.sleep(1 + random.random())
            
            return None

    def _clean_price(self, price_str: str) -> float:
        """Utility to clean price strings."""
        if not price_str: return 0.0
        clean = price_str.replace('€', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(clean)
        except ValueError:
            return 0.0
