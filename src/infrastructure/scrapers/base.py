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
        self.blocked = False # Phase 19: Anti-bot sensor
        self.audit_logger = None # Will be injected by the runner

    @abstractmethod
    async def run(self, context: BrowserContext) -> List[ScrapedOffer]:
        """
        Main entry point for the scraper.
        Must return a list of ScrapedOffer objects.
        """
        pass

    async def _safe_navigate(self, page: Page, url: str) -> bool:
        """
        Helper for robust navigation with error handling, human-like delays, 
        and exponential backoff retries (KAIZEN Hardening).
        """
        import random
        import asyncio
        
        max_retries = 3
        for attempt in range(max_retries):
            # Jittered delay
            delay = random.uniform(2.0, 5.0) * (attempt + 1)
            if attempt > 0:
                logger.info(f"[{self.spider_name}] 🔄 Retry {attempt}/{max_retries} for {url}. Waiting {delay:.2f}s...")
            else:
                logger.info(f"[{self.spider_name}] Humanized delay: {delay:.2f}s before navigating...")
            
            await asyncio.sleep(delay)
            
            try:
                response = await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                api_status = response.status if response else 0
                
                await self._handle_popups(page)
                
                # Check if we were blocked (Anti-bot detection) - Surgical precision
                content = await page.content()
                content_lower = content.lower()
                
                # Active blocking indicators (not just script availability)
                is_blocked = (api_status in [403, 429])
                
                if not is_blocked:
                    # Check for explicit 'blocked' or 'access denied' patterns in body
                    # BUT only if it looks like an error page (short content or specific headers)
                    if len(content) < 2000: # Typical error page size
                        if any(term in content_lower for term in ["blocked", "access denied", "connection reset"]):
                            is_blocked = True
                    
                    # CAPTCHA detection: look for common challenge elements, not just the word 'captcha'
                    if "g-recaptcha" in content_lower or "h-captcha" in content_lower or "cloudflare" in content_lower:
                        # Only if we don't see typical product data
                        if "product" not in content_lower and "price" not in content_lower:
                            is_blocked = True

                if is_blocked:
                    self.blocked = True
                    logger.error(f"[{self.spider_name}] 🚫 DESTIERRO DETECTADO (Status: {api_status}). Anti-bot trigger.")
                    raise Exception(f"Anti-bot block detected (Status: {api_status})")
                
                self.blocked = False # Reset if successful
                return True
            except Exception as e:
                logger.error(f"[{self.spider_name}] Attempt {attempt+1} failed for {url}: {e}")
                if self.audit_logger and attempt == max_retries - 1:
                    self.audit_logger.log_insight(
                        self.spider_name, 
                        "network_failure", 
                        f"Failed after {max_retries} attempts: {e}",
                        severity="error"
                    )
                
        self.errors += 1
        return False

    async def _handle_popups(self, page: Page):
        """
        Hook for closing newsletters, cookie banners, etc.
        To be overridden by child classes if needed.
        """
        pass

    async def _scrape_detail(self, page: Page, url: str) -> dict:
        """
        PRECISION KAIZEN: Navigates to a single product page to extract 
        deep metadata (EAN, GTIN, detailed status, specific images).
        To be implemented by specific scrapers.
        """
        return {}

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
