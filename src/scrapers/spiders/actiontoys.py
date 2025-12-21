import httpx
from typing import List
from src.scrapers.base import BaseSpider, ScrapedOffer
from src.core.logger import logger
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import random

class ActionToysSpider(BaseSpider):
    """
    Spider for ActionToys using WooCommerce Public API (v3) AND Playwright for JS-heavy pages.
    """
    def __init__(self):
        super().__init__(shop_name="ActionToys")
        self.base_url = "https://actiontoys.es/wp-json/wc/store/products"

    async def search(self, query: str) -> List[ScrapedOffer]:
        results = []
        seen_urls = set()

        # Strategy 1: WooCommerce API Search (Fast & Precise)
        if query.lower() == "auto":
             # "Hybrid" means we do both API search AND Category Crawl
             # 1. API Search disabled to prevent noise (Transformers, etc) as per user request
            api_queries = [] 
            
            # 2. HTML Category Crawl (The "Hybrid" Part)
            # This catches items that might not rank in search or have weird names
            category_urls = [
                "https://actiontoys.es/figuras-de-accion/masters-of-the-universe/origins/"
            ]
        else:
            api_queries = [query]
            category_urls = []
            
        # --- PART 1: API SEARCH (HTTPX) ---
        if api_queries:
            async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
                for q in api_queries:
                    logger.info(f"🕸️ ActionToys (API): Searching for '{q}'...")
                    page = 1
                    while True:
                        params = {"search": q, "per_page": 50, "page": page}
                        try:
                            response = await client.get(self.base_url, params=params)
                            if response.status_code != 200: break
                            data = response.json()
                            if not isinstance(data, list) or len(data) == 0: break
                            
                            for item in data:
                                offer = self._parse_api_item(item)
                                if offer and offer.url not in seen_urls:
                                    results.append(offer)
                                    seen_urls.add(offer.url)
                            
                            if len(data) < 50: break
                            page += 1
                            if page > 50: break
                        except Exception as e:
                            logger.error(f"ActionToys API Error: {e}")
                            break
        
        # --- PART 2: HTML CATEGORY CRAWL (PLAYWRIGHT) ---
        if category_urls:
            logger.info("🕸️ ActionToys (Hybrid): Starting Category Crawl via Playwright...")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page_browser = await browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )

                for cat_url in category_urls:
                    page_num = 1
                    while True:
                        # WC Pagination: /page/2/
                        url = cat_url if page_num == 1 else f"{cat_url}page/{page_num}/"
                        logger.info(f"   Crawling (JS): {url}")
                        
                        try:
                            # Navigate using domcontentloaded (faster, less prone to timeouts than networkidle)
                            # Matches successful diagnostic script logic
                            resp = await page_browser.goto(url, timeout=60000, wait_until="domcontentloaded")
                            
                            if resp.status == 404: break
                            
                            # Log Content Length to detect blocks
                            content_len = len(await page_browser.content())
                            logger.info(f"   Page loaded. Content Length: {content_len}")
                            
                            # Wait explicitly
                            # Removed try/except to see actual error
                            await page_browser.locator('li.product').first.wait_for(timeout=15000)

                            # Use Playwright locators
                            product_locators = page_browser.locator('li.product')
                            count = await product_locators.count()
                            
                            if count == 0: 
                                logger.warning("No products found on page.")
                                # Dump details
                                try:
                                    body_html = await page_browser.locator("body").inner_html()
                                    logger.warning(f"BODY DUMP (First 1000): {body_html[:1000]}")
                                    await page_browser.screenshot(path="c:\\Users\\dace8\\OneDrive\\Documentos\\Antigravity\\el_oraculo_de_eternia\\debug_spider_fail_v2.png")
                                    logger.info("Saved debug_spider_fail_v2.png")
                                except Exception as e:
                                    logger.error(f"Failed to dump debug info: {e}")
                                break
                            
                            current_page_found = 0
                            for i in range(count):
                                try:
                                    # Get outer HTML of the element to parse with BS4 (keeping existing parser)
                                    # We use loop index because locator lists can be volatile
                                    element_html = await product_locators.nth(i).evaluate("el => el.outerHTML")
                                    
                                    # Create mini-soup for compatibility
                                    item_soup = BeautifulSoup(element_html, 'html.parser').select_one('li.product')
                                    
                                    if item_soup:
                                        offer = self._parse_html_item(item_soup)
                                        if offer and offer.url not in seen_urls:
                                            results.append(offer)
                                            seen_urls.add(offer.url)
                                            current_page_found += 1
                                except Exception as e:
                                    logger.error(f"Error parsing item {i}: {e}")
                                    continue
                            
                            logger.info(f"   found {current_page_found} items on page {page_num}")
                                    
                            # Stop only if 0 items found AND we are past page 3 (to avoid false negatives on page 1)
                            if current_page_found == 0 and page_num > 3:
                                logger.info("0 items found after page 3. Stopping.")
                                break
                            
                            # Next page check
                            page_num += 1
                            if page_num > 50: break
                            
                            # Sleep slightly
                            await asyncio.sleep(random.uniform(2.0, 4.0))
                            
                        except Exception as e:
                            logger.error(f"html crawl error on page {page_num}: {e}")
                            # Don't break on error, try next page
                            page_num += 1
                            if page_num > 50: break
                            continue
                
                await browser.close()

        logger.info(f"✅ ActionToys (Hybrid): Found {len(results)} total items.")
        return results

    def _parse_api_item(self, item: dict) -> ScrapedOffer | None:
        try:
            name = item.get('name', 'Desconocido')
            # Filter check - REMOVED for "Open Gates" Strategy
            # n_low = name.lower()
            # valid_keywords = ["masters", "origins", "turtles", "skeletor", "he-man", "thundercats", "transformers", "snake men"]
            # if not any(k in n_low for k in valid_keywords): return None

            prices = item.get('prices', {})
            raw_price = prices.get('price', 0)
            try: price_val = float(raw_price) / 100.0
            except: price_val = 0.0
            if price_val == 0.0: return None

            # Image Logic
            images = item.get('images', [])
            img_url = images[0].get('src') if images else None

            return ScrapedOffer(
                product_name=name,
                price=price_val,
                currency="EUR",
                url=item.get('permalink', ''),
                shop_name=self.shop_name,
                is_available=item.get('is_in_stock', True),
                image_url=img_url
            )
        except: return None

    def _parse_html_item(self, item) -> ScrapedOffer | None:
        try:
            # HTML parsing logic for WC standard theme
            # HTML parsing logic for WC standard theme or custom
            # Relaxed selector: Find the first anchor with an href
            a_tag = item.select_one('.woocommerce-LoopProduct-link') or item.select_one('a')
            if not a_tag: 
                logger.warning("Parser: No anchor tag found")
                return None
            
            link = a_tag.get('href')
            
            # Title might be in h2, h3, or just text inside link
            title_tag = item.select_one('.woocommerce-loop-product__title') or item.select_one('h2') or item.select_one('h3')
            name = title_tag.get_text(strip=True) if title_tag else a_tag.get_text(strip=True)
            
            # Price extraction (Prioritize Sale Price)
            # WooCommerce: <del>Old</del> <ins>New</ins>
            price_tag = item.select_one('.price ins bdi') or item.select_one('.price ins .amount')
            
            if not price_tag:
                 # Fallback: Regular price (or non-sale item)
                 price_tag = item.select_one('.price bdi') or item.select_one('.price .amount')
            
            if not price_tag:
                logger.warning(f"Parser: No price found for {name}")
                return None
            
            # Clean price string explicitly
            price_txt = price_tag.get_text(strip=True).replace('€', '').replace(',', '.').replace('&nbsp;', '')
            try:
                price_val = float(price_txt)
            except:
                logger.warning(f"Parser: Could not float price '{price_txt}' for {name}")
                return None

            # Legacy logic removed. Price is already extracted above.
            # price_tag legacy block deleted to prevent double jeopardy.
            
            is_avl = True
            # Check "out of stock" badge if exists
            if item.select_one('.out-of-stock-badge'): is_avl = False

            # Image Logic HTML
            img_tag = item.select_one('img')
            img_url = None
            if img_tag:
                 img_url = img_tag.get('data-src') or img_tag.get('src') or img_tag.get('data-lazy-src')

            return ScrapedOffer(
                product_name=name,
                price=price_val,
                currency="EUR",
                url=link,
                shop_name=self.shop_name,
                is_available=is_avl,
                image_url=img_url
            )
        except Exception: return None

    # Legacy method wrapper if needed, but we used separate methods above
    def _parse_item(self, item: dict) -> ScrapedOffer | None:
        return self._parse_api_item(item)
