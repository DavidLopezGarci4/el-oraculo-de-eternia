from typing import List, Optional
import asyncio
import logging
from playwright.async_api import BrowserContext, Page
from bs4 import BeautifulSoup

from src.infrastructure.scrapers.base import BaseScraper
from src.scrapers.base import ScrapedOffer

# Configure Logger
logger = logging.getLogger(__name__)

class FantasiaScraper(BaseScraper):
    """
    Scraper for Fantasia Personajes (PrestaShop).
    Uses 'content' attribute for price reliability.
    """
    def __init__(self):
        super().__init__(name="Fantasia", base_url="https://fantasiapersonajes.es/busqueda?controller=search&s=masters+of+the+universe")

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
                
                # Strategy 1: Auditor's Recommendation (JSON-LD)
                json_products = self._extract_from_json_ld(soup)
                if json_products:
                    logger.info(f"[{self.spider_name}] ⚡ Used JSON-LD extraction for {len(json_products)} items.")
                    products.extend(json_products)
                    self.items_scraped += len(json_products)
                else:
                    # Strategy 2: Verified CSS Selectors (Fallback)
                    items = soup.select('article.product-miniature')
                    logger.info(f"[{self.spider_name}] Found {len(items)} items using CSS.")
                    
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
            
            if price_span:
                # Try attribute first
                if price_span.has_attr('content'):
                    try:
                        price_val = float(price_span['content'])
                    except:
                        pass
                
                # Fallback to text cleaning if attribute fails or is missing
                if price_val == 0.0:
                    price_val = self._normalize_price(price_span.get_text(strip=True))
            
            if price_val == 0.0:
                # One last attempt: look for meta[itemprop="price"] inside item
                meta_price = item.select_one('meta[itemprop="price"]')
                if meta_price and meta_price.has_attr('content'):
                    price_val = self._normalize_price(meta_price['content'])
            
            if price_val == 0.0:
                return None

            # 3. Availability
            is_avl = True
            # Check for 'product-unavailable' class
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

    def _extract_from_json_ld(self, soup) -> List[ScrapedOffer]:
        """
        Attempts to parse schema.org JSON-LD data.
        Looking for @type: ItemList or list of Product.
        """
        import json
        scraped = []
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.get_text(strip=True))
                    
                    # Normalizing list vs dict
                    if isinstance(data, dict):
                        data_list = [data]
                    else:
                        data_list = data
                        
                    for entry in data_list:
                        item_type = entry.get('@type')
                        
                        # Handle "ItemList" which contains "itemListElement"
                        if item_type == 'ItemList' and 'itemListElement' in entry:
                            for pos in entry['itemListElement']:
                                # Sometimes it's just a URL, sometimes a full object
                                item = pos.get('item', {})
                                if item and item.get('@type') == 'Product':
                                    prod = self._parse_json_product(item)
                                    if prod: scraped.append(prod)
                                    
                        # Handle direct "Product"
                        elif item_type == 'Product':
                            prod = self._parse_json_product(entry)
                            if prod: scraped.append(prod)
                            
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.warning(f"[{self.spider_name}] JSON-LD Error: {e}")
            
        return scraped

    def _parse_json_product(self, data: dict) -> Optional[ScrapedOffer]:
        try:
            name = data.get('name')
            link = data.get('url')
            img_url = data.get('image')
            
            # Ensure URL is absolute
            if img_url and isinstance(img_url, list):
                img_url = img_url[0]
            
            # Price parsing from 'offers'
            offers = data.get('offers', {})
            # It can be a list or dict
            if isinstance(offers, list):
                if not offers: return None
                offers = offers[0]
                
            price = offers.get('price')
            currency = offers.get('priceCurrency', 'EUR')
            status = offers.get('availability', 'InStock')
            
            if not name or not price: return None
            
            is_avl = "InStock" in status
            
            return ScrapedOffer(
                product_name=name,
                price=float(price),
                currency=currency,
                url=link,
                shop_name=self.spider_name,
                is_available=is_avl,
                image_url=img_url
            )
        except Exception:
            return None

    async def _scrape_detail(self, page: Page, url: str) -> dict:
        """
        Fantasia specific: Extract EAN/Referencia.
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
        Fantasia specific: Close the 'LOGÍSTICA REYES' modal and accept cookies.
        """
        try:
            # 1. Logistics Modal
            # Based on audit, it has a "CERRAR AVISO" button.
            close_modal = page.locator("button:has-text('CERRAR AVISO'), .modal-header .close")
            if await close_modal.is_visible(timeout=3000):
                logger.info(f"[{self.spider_name}] 📦 Closing Logistics modal...")
                await close_modal.click()
                await asyncio.sleep(0.5)

            # 2. Cookie Banner
            accept_cookies = page.locator("button:has-text('ACEPTO')")
            if await accept_cookies.is_visible(timeout=2000):
                logger.info(f"[{self.spider_name}] 🍪 Accepting cookies...")
                await accept_cookies.click()
                await asyncio.sleep(0.5)
        except Exception:
            pass
