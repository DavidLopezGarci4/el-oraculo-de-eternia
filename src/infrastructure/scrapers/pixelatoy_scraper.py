from typing import List, Optional
import asyncio
import logging
from playwright.async_api import BrowserContext, Page
from bs4 import BeautifulSoup

from src.infrastructure.scrapers.base import BaseScraper
from src.scrapers.base import ScrapedOffer

# Configure Logger
logger = logging.getLogger(__name__)

class PixelatoyScraper(BaseScraper):
    """
    Scraper for Pixelatoy (PrestaShop).
    Uses 'itemprop' and specific PrestaShop selectors.
    """
    def __init__(self):
        super().__init__(name="Pixelatoy", base_url="https://pixelatoy.com/es/busqueda?controller=search&s=masters+of+the+universe")

    async def run(self, context: BrowserContext) -> List[ScrapedOffer]:
        products: List[ScrapedOffer] = []
        page = await context.new_page()
        
        try:
            current_url = self.base_url
            page_num = 1
            max_pages = 5
            
            while current_url and page_num <= max_pages:
                logger.info(f"[{self.spider_name}] Scraping page {page_num}: {current_url}")
                
                if not await self._safe_navigate(page, current_url):
                    break
                
                await asyncio.sleep(2.0)
                
                html_content = await page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Container
                items = soup.select('article.product-miniature')
                logger.info(f"[{self.spider_name}] Found {len(items)} items on page {page_num}")
                
                for item in items:
                    prod = self._parse_html_item(item)
                    if prod:
                        products.append(prod)
                        self.items_scraped += 1
                
                # Pagination
                next_tag = soup.select_one('a.next.js-search-link')
                if next_tag and next_tag.get('href'):
                    current_url = next_tag.get('href')
                    page_num += 1
                else:
                    logger.info(f"[{self.spider_name}] End of pagination.")
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
            a_tag = item.select_one('h3.h3.product-title a')
            if not a_tag: return None
            
            link = a_tag.get('href')
            name = a_tag.get_text(strip=True)
            
            # 2. Price (PrestaShop Content Attribute Pattern)
            price_val = 0.0
            price_span = item.select_one('span.price')
            
            if price_span and price_span.has_attr('content'):
                # Best reliability: content="29.99"
                try:
                    price_val = float(price_span['content'])
                except:
                    pass
            
            if price_val == 0.0 and price_span:
                # Fallback to text
                price_val = self._normalize_price(price_span.get_text(strip=True))
            
            if price_val == 0.0:
                return None

            # 3. Availability
            is_avl = True
            # Check for 'product-unavailable' class on the flags
            if item.select_one('.product-unavailable'):
                is_avl = False
            
            # 4. Image
            img_tag = item.select_one('img')
            img_url = None
            if img_tag:
                 img_url = img_tag.get('data-src') or img_tag.get('src') 

            return ScrapedOffer(
                product_name=name,
                price=price_val,
                currency="EUR",
                url=link,
                shop_name=self.spider_name,
                is_available=is_avl,
                image_url=img_url
            )
        except Exception as e:
            logger.warning(f"[{self.spider_name}] Item parsing error: {e}")
            return None

    async def _scrape_detail(self, page: Page, url: str) -> dict:
        """
        Pixelatoy specific: Extract EAN/Referencia.
        """
        if not await self._safe_navigate(page, url):
            return {}
        
        try:
            # Selector from audit: .product-reference span[itemprop="sku"]
            ean_tag = page.locator(".product-reference span[itemprop='sku']")
            if await ean_tag.is_visible(timeout=3000):
                ean = await ean_tag.inner_text()
                return {"ean": ean.strip()}
        except Exception:
            pass
        return {}

    async def _handle_popups(self, page: Page):
        pass
