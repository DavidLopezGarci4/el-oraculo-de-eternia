from scrapers.base import AsyncScraperPlugin
from models import ProductOffer
from logger import log_structured
from bs4 import BeautifulSoup
import time
import urllib.parse

class ElectropolisScraper(AsyncScraperPlugin):
    """
    Async Scraper for Electropolis.
    Target: https://www.electropolis.es/zona-freaky/figuras/figuras.html?licencia=99325&marcas=92264&product_list_dir=asc
    """
    
    @property
    def name(self) -> str:
        return "Electropolis"

    @property
    def base_url(self) -> str:
        return "https://www.electropolis.es/zona-freaky/figuras/figuras.html"

    async def search(self, query: str) -> list[ProductOffer]:
        start_time = time.time()
        products = []
        seen_urls = set()
        
        # Facet Params from User
        # licencia=99325 (Masters likely)
        # marcas=92264 (Mattel likely)
        
        page = 1
        has_more = True
        
        while has_more and page <= 10:
            params = {
                "licencia": "99325",
                "marcas": "92264",
                "product_list_dir": "asc",
                "p": page # Standard Magento/Varien pagination param 'p'
            }
            
            try:
                html = await self.fetch(self.base_url, params=params)
                if not html: break
                
                soup = BeautifulSoup(html, 'html.parser')
                items = soup.select('.item.product.product-item') # Standard Magento classes
                
                if not items:
                    break
                
                new_items_count = 0
                for item in items:
                    try:
                        title_elem = item.select_one('.product-item-link')
                        if not title_elem: continue
                        
                        title = title_elem.get_text(strip=True)
                        link = title_elem.get('href')
                        
                        if link in seen_urls: continue
                        seen_urls.add(link)
                        
                        img_elem = item.select_one('.product-image-photo')
                        image_url = img_elem.get('src') if img_elem else None
                        
                        price_elem = item.select_one('.price')
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

                # Pagination Check
                pages_item_next = soup.select_one('.pages-item-next')
                if not pages_item_next:
                    has_more = False
                
                page += 1
                
            except Exception as e:
                self.logger.error(f"Error scraping Electropolis page {page}: {e}")
                break
            
        duration = time.time() - start_time
        log_structured("SCRAPE_END", self.name, items_found=len(products), duration_seconds=round(duration, 2))
        return products
