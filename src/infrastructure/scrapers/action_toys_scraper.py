from typing import List, Optional
import asyncio
import logging
from playwright.async_api import BrowserContext, Page
from bs4 import BeautifulSoup

from src.infrastructure.scrapers.base import BaseScraper
from src.scrapers.base import ScrapedOffer

# Configure Logger
logger = logging.getLogger(__name__)

class ActionToysScraper(BaseScraper):
    """
    Scraper for ActionToys (WooCommerce).
    """
    def __init__(self):
        super().__init__(name="ActionToys", base_url="https://actiontoys.es/figuras-de-accion/masters-of-the-universe/")

    async def run(self, context: BrowserContext) -> List[ScrapedOffer]:
        """
        Executes the scraping logic for Action Toys.
        """
        products: List[ScrapedOffer] = []
        page = await context.new_page()
        
        try:
            # Start at page 1
            current_url = self.base_url
            page_num = 1
            max_pages = 100 # Future-proof: Follows the 'Next' link up to 100 pages
            
            while current_url and page_num <= max_pages:
                logger.info(f"[{self.spider_name}] Scraping page {page_num}: {current_url}")
                
                if not await self._safe_navigate(page, current_url):
                    break
                
                # Random delay to behave like a human (anti-ban)
                await asyncio.sleep(2.0)
                
                # Extract HTML
                html_content = await page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find Items
                items = soup.select('li.product')
                logger.info(f"[{self.spider_name}] Found {len(items)} items on page {page_num}")
                
                for item in items:
                    prod = self._parse_html_item(item)
                    if prod:
                        products.append(prod)
                        self.items_scraped += 1
                
                # Pagination (More robust selector: looking for current + 1 or next)
                next_tag = soup.select_one('a.next.page-numbers')
                if not next_tag:
                    # Fallback: check the pagination list for the link AFTER the current one
                    current_span = soup.select_one('span.page-numbers.current')
                    if current_span and current_span.parent:
                        next_li = current_span.parent.find_next_sibling('li')
                        if next_li:
                            next_tag = next_li.select_one('a.page-numbers')

                if next_tag and next_tag.get('href'):
                    current_url = next_tag.get('href')
                    if not current_url.startswith('http'):
                        current_url = f"https://actiontoys.es{current_url}"
                    page_num += 1
                else:
                    # HEURISTIC: Check if there's any other indicator of a next page
                    logger.info(f"[{self.spider_name}] No more explicit 'Next' links found.")
                    break
                    
        except Exception as e:
            logger.error(f"[{self.spider_name}] Critical Error: {e}", exc_info=True)
            self.errors += 1
        finally:
            await page.close()
            
        logger.info(f"[{self.spider_name}] Finished. Total items: {len(products)}")
        return products

    def _parse_html_item(self, item) -> Optional[ScrapedOffer]:
        try:
             # 1. Link & Name
            a_tag = item.select_one('.woocommerce-LoopProduct-link') or item.select_one('a')
            if not a_tag: return None
            
            link = a_tag.get('href')
            
            title_tag = item.select_one('.woocommerce-loop-product__title') or item.select_one('h2') or item.select_one('h3')
            name = title_tag.get_text(strip=True) if title_tag else a_tag.get_text(strip=True)
            
            # 2. Price (WooCommerce Pattern)
            # Priority: <ins> (Sale price) -> bdi (Regular price)
            price_val = 0.0
            
            # Check for Sale Price first
            ins_tag = item.select_one('ins .amount bdi')
            if ins_tag:
                 price_val = self._extract_price_text(ins_tag)
            else:
                # Regular price
                price_tag = item.select_one('.price bdi')
                if not price_tag:
                     price_tag = item.select_one('.price .amount')
                
                if price_tag:
                    price_val = self._extract_price_text(price_tag)
            
            if price_val == 0.0:
                return None

            # 3. Availability
            is_avl = True
            if item.select_one('.out-of-stock-badge'): 
                is_avl = False
            
            return ScrapedOffer(
                product_name=name,
                price=price_val,
                currency="EUR",
                url=link,
                shop_name=self.spider_name,
                is_available=is_avl
            )
        except Exception as e:
            logger.warning(f"[{self.spider_name}] Item parsing error: {e}")
            return None

    async def _scrape_detail(self, page: Page, url: str) -> dict:
        """
        ActionToys specific: Extract GTIN/EAN.
        """
        if not await self._safe_navigate(page, url):
            return {}
        
        try:
            # Selector from audit: .product_meta .hwp-gtin span
            gtin_tag = page.locator(".product_meta .hwp-gtin span")
            if await gtin_tag.is_visible(timeout=3000):
                ean = await gtin_tag.inner_text()
                return {"ean": ean.strip()}
        except Exception:
            pass
        return {}

    async def _handle_popups(self, page: Page):
        pass

    def _extract_price_text(self, tag) -> float:
        """Helper to extract float from bdi/span tag"""
        txt = tag.get_text(strip=True).replace('&nbsp;', '')
        return self._normalize_price(txt)
