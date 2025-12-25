from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, HttpUrl
from datetime import datetime

class ScrapedOffer(BaseModel):
    product_name: str
    price: float
    currency: str = "EUR"
    url: str
    shop_name: str
    is_available: bool = True
    image_url: Optional[str] = None
    ean: Optional[str] = None
    scraped_at: datetime = datetime.utcnow()

class BaseSpider(ABC):
    """
    Abstract Base Class for all Spiders.
    Enforces a common interface for the Pipeline.
    """
    def __init__(self, shop_name: str):
        self.shop_name = shop_name

    def _get_random_header(self) -> dict:
        """
        Returns a header dict with a random User-Agent to avoid fingerprinting.
        """
        import random
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        return {
            "User-Agent": random.choice(user_agents),
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com/"
        }

    async def _random_sleep(self, min_sec: float = 1.0, max_sec: float = 3.5):
        """
        Sleeps for a random duration to emulate human behavior.
        """
        import asyncio
        import random
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    @abstractmethod
    async def search(self, query: str) -> List[ScrapedOffer]:
        """
        Search for a product by name.
        Returns a list of offers found.
        """
        pass
