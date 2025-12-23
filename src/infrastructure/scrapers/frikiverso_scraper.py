from typing import List, Optional
import asyncio
import logging
from playwright.async_api import BrowserContext, Page
from bs4 import BeautifulSoup

from src.infrastructure.scrapers.base import BaseScraper
from src.scrapers.base import ScrapedOffer

# Configure Logger
logger = logging.getLogger(__name__)

class FrikiversoScraper(BaseScraper):
    """
    Scraper for Frikiverso (PrestaShop).
    Parsing requires robust text cleaning as <span class="price"> text is often messy.
    """
    def __init__(self):
        super().__init__(name="Frikiverso", base_url="https://frikiverso.es/es/buscar?controller=search&s=masters+del+universo")

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
                
                # PrestaShop standard container
                items = soup.select('article.js-product-miniature')
                logger.info(f"[{self.spider_name}] Found {len(items)} items on page {page_num}")
                
                for item in items:
                    prod = self._parse_html_item(item)
                    if prod:
                        products.append(prod)
                        self.items_scraped += 1
                
                # Pagination
                # Frikiverso uses nav.pagination ul li a.next
                next_tag = soup.select_one('a.next.page-link')
                if not next_tag:
                    next_tag = soup.select_one('.pagination .next a')
                    
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
            # Frikiverso: h3.s_title_block a
            a_tag = item.select_one('h3.s_title_block a') or item.select_one('h3.product-title a')
            if not a_tag: return None
            
            link = a_tag.get('href')
            name = a_tag.get_text(strip=True)
            
            # 2. Price (PrestaShop Text Pattern)
            price_val = 0.0
            price_span = item.select_one('span.price')
            
            if price_span:
                # Text parsing "25,32 €"
                raw_txt = price_span.get_text(strip=True)
                price_val = self._normalize_price(raw_txt)
            
            if price_val == 0.0:
                return None

            # 3. Availability
            is_avl = True
            
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
