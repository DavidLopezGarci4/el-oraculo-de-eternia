from scrapers.base import AsyncScraperPlugin
from models import ProductOffer
from logger import log_structured
from bs4 import BeautifulSoup
import time
import urllib.parse
import asyncio

class FantasiaScraper(AsyncScraperPlugin):
    """
    Async Scraper for Fantasia Personajes (PrestaShop).
    Uses 'resultsPerPage=100' + Async Pagination to ensure full coverage.
    """
    
    @property
    def name(self) -> str:
        return "Fantasia Personajes"

    @property
    def base_url(self) -> str:
        return "https://fantasiapersonajes.es/buscar"

    async def search(self, query: str) -> list[ProductOffer]:
        start_time = time.time()
        products = []
        seen_urls = set()
        
        # We will attempt to fetch up to 10 pages concurrently to be fast,
        # but PrestaShop Search usually puts everything in few pages if we raise resultsPerPage.
        # Let's try sequential-async loop to be reliable and stop exactly when needed.
        
        page = 1
        has_more = True
        consecutive_empty = 0
        
        while has_more and page <= 10: # Safety limit 10 pages * 100 items = 1000 items
            params = {
                "controller": "search",
                "s": query,
                "order": "product.position.desc",
                "resultsPerPage": "100", # Max reliable usually
                "page": page
            }
            
            try:
                html = await self.fetch(self.base_url, params=params)
                if not html:
                    break
                
                soup = BeautifulSoup(html, 'html.parser')
                items = soup.select('.product-miniature')
                
                if not items:
                    break
                
                new_items_count = 0
                for item in items:
                    try:
                        title_elem = item.select_one('.product-title a')
                        if not title_elem: continue
                        
                        title = title_elem.get_text(strip=True)
                        link = title_elem.get('href')
                        
                        if link in seen_urls: continue
                        seen_urls.add(link)
                        
                        img_elem = item.select_one('.thumbnail-container img')
                        image_url = None
                        if img_elem:
                            image_url = img_elem.get('data-src') or img_elem.get('src')
                        
                        price_elem = item.select_one('.product-price') or item.select_one('.price')
                        price_str = price_elem.get_text(strip=True) if price_elem else "0.00€"
                        
                        offer = ProductOffer(
                            name=title,
                            price_val=self._clean_price(price_str),
                            currency="€",
                            url=link,
                            image_url=image_url,
                            store_name=self.name,
                            display_price=price_str
                        )
                        products.append(offer)
                        new_items_count += 1
                        
                    except Exception:
                        continue
                        
                if new_items_count == 0:
                     consecutive_empty += 1
                else:
                     consecutive_empty = 0
                     
                if consecutive_empty >= 2:
                    break
                
                # Check for "next" button to be sure
                next_btn = soup.select_one('.next')
                if not next_btn:
                    has_more = False
                
                page += 1
                
            except Exception as e:
                self.logger.error(f"Error scraping Fantasia page {page}: {e}")
                break
        
        duration = time.time() - start_time
        log_structured("SCRAPE_END", self.name, items_found=len(products), duration_seconds=round(duration, 2))
        return products
