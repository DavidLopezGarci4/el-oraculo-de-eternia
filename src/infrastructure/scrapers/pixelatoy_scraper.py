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
            max_pages = 25 # Increased for safety
            
            while current_url and page_num <= max_pages:
                logger.info(f"[{self.spider_name}] Scraping page {page_num}: {current_url}")
                
                if not await self._safe_navigate(page, current_url):
                    break
                
                await self._handle_popups(page)
                await asyncio.sleep(2.0) 
                
                # Human-like interaction (Kaizen Hardening)
                await page.mouse.wheel(0, 500)
                await asyncio.sleep(1.0)
                
                html_content = await page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Container (Refined with js- variant for PrestaShop modern themes)
                items = soup.select('article.product-miniature, article.js-product-miniature')
                logger.info(f"[{self.spider_name}] Found {len(items)} items on page {page_num}")
                
                if not items:
                    logger.warning(f"[{self.spider_name}] No items found on page {page_num}. Possible block or selector change.")
                    break

                for item in items:
                    prod = self._parse_html_item(item)
                    if prod:
                        products.append(prod)
                        self.items_scraped += 1
                
                # Pagination: PrestaShop .next.js-search-link
                next_tag = soup.select_one('a.next.js-search-link, .pagination .next a, a#infinity-url')
                if next_tag and next_tag.get('href') and 'javascript:void' not in next_tag.get('href'):
                    current_url = next_tag.get('href')
                    if current_url.startswith('/'):
                        current_url = f"https://www.pixelatoy.com{current_url}"
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
            a_tag = item.select_one('.product-title a, h3.product-title a')
            if not a_tag: return None
            
            link = a_tag.get('href')
            name = a_tag.get_text(strip=True)
            
            if link and link.startswith('/'):
                 link = f"https://www.pixelatoy.com{link}"

            # 2. Price (PrestaShop Content Attribute Pattern)
            price_val = 0.0
            # Current display price selector from audit
            price_span = item.select_one('.product-price, span.product-price, span.price')
            
            if price_span:
                # Try attribute first (very reliable for EUR)
                if price_span.has_attr('content'):
                    try:
                        price_val = float(price_span['content'].replace(',', '.'))
                    except:
                        pass
                
                # Fallback to text cleaning
                if price_val == 0.0:
                    price_val = self._normalize_price(price_span.get_text(strip=True))
            
            # Additional fallback check
            if price_val == 0.0:
                 meta_price = item.select_one('meta[itemprop="price"]')
                 if meta_price and meta_price.has_attr('content'):
                     try:
                         price_val = float(meta_price['content'].replace(',', '.'))
                     except:
                         pass

            if price_val == 0.0:
                logger.debug(f"[{self.spider_name}] Skipping item {name} - Price could not be parsed.")
                return None

            # 3. Availability
            is_avl = True
            # Check for 'product-unavailable' class (Agotado)
            if item.select_one('.product-unavailable, .out-of-stock'):
                is_avl = False
            
            # 4. Image
            img_tag = item.select_one('img')
            img_url = None
            if img_tag:
                 img_url = img_tag.get('data-src') or img_tag.get('src') 
                 if img_url and img_url.startswith('/'):
                     img_url = f"https://www.pixelatoy.com{img_url}"

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
        """
        Pixelatoy specific: Close cookie banners and newsletters.
        """
        try:
            # Common PrestaShop cookie accept button + Pixelatoy specific
            accept_btn = page.locator("#iqitcookielaw-accept, button:has-text('ACEPTAR'), .btn-primary:has-text('Aceptar'), button[aria-label='Accept']")
            if await accept_btn.is_visible(timeout=3000):
                logger.info(f"[{self.spider_name}] 🍪 Accepting cookies...")
                await accept_btn.click()
                await asyncio.sleep(0.5)
            
            # Additional newsletter check (iqitnewsletter)
            close_newsletter = page.locator(".iqitnewsletter-close, #iqitnewsletter-close")
            if await close_newsletter.is_visible(timeout=2000):
                logger.info(f"[{self.spider_name}] 📧 Closing newsletter...")
                await close_newsletter.click()
        except Exception:
            pass
