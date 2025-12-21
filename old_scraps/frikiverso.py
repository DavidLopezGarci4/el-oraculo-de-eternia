from scrapers.base import AsyncScraperPlugin
from models import ProductOffer
from logger import log_structured
from bs4 import BeautifulSoup
import time
import urllib.parse

class FrikiversoScraper(AsyncScraperPlugin):
    """
    Async Scraper for Frikiverso.
    STRATEGY: Category Facet Scraping (Reliable) instead of Search (Unreliable).
    Target: https://frikiverso.es/es/149-figuras with MOTU Filters.
    """
    
    @property
    def name(self) -> str:
        return "Frikiverso"

    @property
    def base_url(self) -> str:
        # User provided specific category endpoint
        return "https://frikiverso.es/es/149-figuras"

    async def search(self, query: str) -> list[ProductOffer]:
        start_time = time.time()
        products = []
        seen_urls = set()
        
        page = 1
        has_more = True
        
        # Filter for "Masters del Universo" + "Mattel"
        # q=Licencia-Masters+del+Universo/Marca-Mattel
        facet_query = "Licencia-Masters+del+Universo/Marca-Mattel"
        
        while has_more and page <= 20: # Safety limit
            params = {
                "q": facet_query,
                "order": "product.position.desc", # Or price? User used price.asc in example. Let's use default or relevance. User used price.asc.
                "page": page
            }
            
            try:
                # Note: 'q' param usually doesn't work well with encoded params in aiohttp if slashes are involved.
                # We might need to construct URL manually if aiohttp encodes '/' as '%2F'.
                # PrestaShop facets use '/' as separator.
                # Let's try manual URL construction for safety.
                
                url = f"{self.base_url}?q={facet_query}&page={page}"
                
                self.logger.info(f"Scraping Frikiverso: {url}")
                html = await self.fetch(url) # Params handled in string
                
                if not html: break
                
                soup = BeautifulSoup(html, 'html.parser')
                items = soup.select('.js-product-miniature')
                
                if not items:
                    break
                
                new_items_count = 0
                for item in items:
                    try:
                        title_elem = item.select_one('.s_title_block a')
                        if not title_elem: continue
                        
                        title = title_elem.get_text(strip=True)
                        link = title_elem.get('href')
                        
                        if link in seen_urls: continue
                        seen_urls.add(link)
                        
                        img_elem = item.select_one('.front-image')
                        image_url = img_elem.get('data-src') or img_elem.get('src') if img_elem else None
                        
                        price_elem = item.select_one('.product-price-and-shipping .price')
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
                    break

                # Pagination check
                # Check for "next" class in pagination
                next_disabled = soup.select_one('.pagination .next.disabled')
                if next_disabled:
                    has_more = False
                
                # If we cannot find pagination controls but found items, maybe it's just one page.
                # If we found full page (e.g. 12 items? grid is small), assume next.
                # Safer: check if '.next' exists at all
                next_exists = soup.select_one('.pagination .next')
                if not next_exists:
                    has_more = False
                    
                page += 1
                
            except Exception as e:
                self.logger.error(f"Error scraping Frikiverso page {page}: {e}")
                break
            
        duration = time.time() - start_time
        log_structured("SCRAPE_END", self.name, items_found=len(products), duration_seconds=round(duration, 2))
        return products
