from typing import List, Optional
import asyncio
import logging
from playwright.async_api import BrowserContext, Page
from bs4 import BeautifulSoup

from src.infrastructure.scrapers.base import BaseScraper
from src.scrapers.base import ScrapedOffer

# Configure Logger
logger = logging.getLogger(__name__)

class ElectropolisScraper(BaseScraper):
    """
    Scraper for Electropolis (Magento 2).
    Uses robust 'data-price-amount' attribute for zero-ambiguity pricing.
    """
    def __init__(self):
        super().__init__(name="Electropolis", base_url="https://www.electropolis.es/catalogsearch/result/?q=masters+of+the+universe")

    async def run(self, context: BrowserContext) -> List[ScrapedOffer]:
        products: List[ScrapedOffer] = []
        page = await context.new_page()
        
        try:
            current_url = self.base_url
            page_num = 1
            max_pages = 5
            
            while current_url and page_num <= max_pages:
                logger.info(f"[{self.spider_name}] Scraping page {page_num}: {current_url}")
                
                # Navigate
                await page.goto(current_url, wait_until="domcontentloaded")
                
                # Smart Wait (Auditor Recommendation)
                try:
                    # Wait for the main product container to appear
                    await page.wait_for_selector('.product-item-info', timeout=15000)
                except Exception:
                    logger.warning(f"[{self.spider_name}] Timeout waiting for selectors on {current_url}")
                
                # Get content regardless of wait success
                html_content = await page.content()
                
                # Small human courtesy delay still recommended, but smaller
                await asyncio.sleep(1.0) 
                soup = BeautifulSoup(html_content, 'html.parser')
                
                items = soup.select('.product-item-info')
                logger.info(f"[{self.spider_name}] Found {len(items)} items on page {page_num}")
                
                for item in items:
                    prod = self._parse_html_item(item)
                    if prod:
                        products.append(prod)
                        self.items_scraped += 1
                
                # Pagination: Magento uses .pages .action.next
                next_tag = soup.select_one('.pages .action.next')
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
            a_tag = item.select_one('a.product-item-link')
            if not a_tag: return None
            
            link = a_tag.get('href')
            name = a_tag.get_text(strip=True)
            
            # 2. Price (Magento 2 Robust Pattern)
            price_val = 0.0
            price_container = item.select_one('[data-price-type="finalPrice"]')
            
            if price_container and price_container.has_attr('data-price-amount'):
                # Best case: clean float in attribute
                try:
                    price_val = float(price_container['data-price-amount'])
                except:
                    pass
            else:
                # Fallback to text
                price_span = item.select_one('.price')
                if price_span:
                    price_val = self._normalize_price(price_span.get_text(strip=True))
            
            if price_val == 0.0:
                return None

            # 3. Availability
            is_avl = True
            if item.select_one('.stock.unavailable'):
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
        Electropolis specific: Extract EAN from JSON-LD or More info tab.
        """
        if not await self._safe_navigate(page, url):
            return {}
        
        try:
            # Strategy A: JSON-LD (Fastest)
            # From audit: gtin13 exists in Product schema
            gtin = await page.evaluate("""() => {
                const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
                for (let s of scripts) {
                    try {
                        const data = JSON.parse(s.textContent);
                        if (data['@type'] === 'Product' && data.gtin13) return data.gtin13;
                    } catch (e) {}
                }
                return null;
            }""")
            if gtin: return {"ean": str(gtin)}

            # Strategy B: Technical Specs table
            # Audit note: Needs click on #tab-label-additional
            tab = page.locator("#tab-label-additional")
            if await tab.is_visible(timeout=2000):
                await tab.click()
                ean_val = page.locator('#product-attribute-specs-table tr td[data-th="Código EAN"]')
                if await ean_val.is_visible(timeout=2000):
                    return {"ean": await ean_val.inner_text()}
        except Exception:
            pass
        return {}

    async def _handle_popups(self, page: Page):
        """
        Electropolis specific: Accept cookies to clear the overlay.
        """
        try:
            # Selector derived from audit
            accept_btn = page.locator("button:has-text('ACEPTAR COOKIES')")
            if await accept_btn.is_visible(timeout=3000):
                logger.info(f"[{self.spider_name}] 🍪 Accepting cookies...")
                await accept_btn.click()
                await asyncio.sleep(1.0)
        except Exception:
            pass
