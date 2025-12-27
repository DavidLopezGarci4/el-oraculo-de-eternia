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
            max_pages = 25 # Increased for MOTU catalog
            
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
                
                # PrestaShop standard container
                items = soup.select('article.js-product-miniature, article.ajax_block_product')
                logger.info(f"[{self.spider_name}] Found {len(items)} items on page {page_num}")
                
                if not items:
                    logger.warning(f"[{self.spider_name}] No items found. Possible selector change or end of list.")
                    break

                for item in items:
                    prod = self._parse_html_item(item)
                    if prod:
                        products.append(prod)
                        self.items_scraped += 1
                
                # Pagination
                # Frikiverso uses a.next.js-search-link
                next_tag = soup.select_one('a.next.js-search-link, .pagination a.next, a[rel="next"]')
                if next_tag and next_tag.get('href') and 'javascript' not in next_tag.get('href'):
                    current_url = next_tag.get('href')
                    if current_url.startswith('/'):
                        current_url = f"https://frikiverso.es{current_url}"
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
            a_tag = item.select_one('.product-title a, h3.s_title_block a, h3.product-title a')
            if not a_tag: return None
            
            link = a_tag.get('href')
            name = a_tag.get_text(strip=True)
            
            if link and link.startswith('/'):
                 link = f"https://frikiverso.es{link}"

            # 2. Price (PrestaShop Text Pattern)
            price_val = 0.0
            price_span = item.select_one('.product-price-and-shipping .price, span.price')
            
            if price_span:
                # Text parsing "25,32 €"
                raw_txt = price_span.get_text(strip=True)
                price_val = self._normalize_price(raw_txt)
            
            if price_val == 0.0:
                # Try to find price in meta tags within the article
                meta_price = item.select_one('meta[itemprop="price"]')
                if meta_price and meta_price.has_attr('content'):
                    try:
                        price_val = float(meta_price['content'].replace(',', '.'))
                    except:
                        pass

            if price_val == 0.0:
                return None

            # 3. Availability
            is_avl = True
            # Check for specific flags or classes
            if item.select_one('.product-flag.out_of_stock, .out-of-stock, .product-unavailable'):
                is_avl = False
            
            # 4. Image
            img_tag = item.select_one('.product-thumbnail img, img')
            img_url = None
            if img_tag:
                 img_url = img_tag.get('data-src') or img_tag.get('src')
                 if img_url and img_url.startswith('/'):
                     img_url = f"https://frikiverso.es{img_url}"

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

    async def _handle_popups(self, page: Page):
        """
        Frikiverso specific: Close cookie banners and newsletter popups.
        """
        try:
            # Cookie Consent (CookieScript)
            accept_cookies = page.locator("#cookiescript_accept")
            if await accept_cookies.is_visible(timeout=3000):
                logger.info(f"[{self.spider_name}] 🍪 Accepting cookies...")
                await accept_cookies.click()
                await asyncio.sleep(0.5)

            # Newsletter popup
            close_btn = page.locator(".newsletter-popup button.close, .newsletter-close, button[aria-label='Close'], #st_newsletter_popup .close")
            if await close_btn.is_visible(timeout=2000):
                logger.info(f"[{self.spider_name}] 🤫 Closing newsletter popup...")
                await close_btn.click()
                await asyncio.sleep(0.5)
        except Exception:
            pass

    async def _scrape_detail(self, page: Page, url: str) -> dict:
        """
        Frikiverso specific: Extract EAN from detail page.
        """
        if not await self._safe_navigate(page, url):
            return {}
        
        try:
            # Audit showed it's inside .product-prices near a <strong>EAN:</strong>
            # We'll use JS for precision
            ean = await page.evaluate("""() => {
                const label = Array.from(document.querySelectorAll('strong')).find(st => st.textContent.includes('EAN:'));
                return label ? label.parentElement.innerText.replace('EAN:', '').trim() : null;
            }""")
            return {"ean": ean} if ean else {}
        except Exception:
            return {}
