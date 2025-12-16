from scrapers.base import AsyncScraperPlugin
from models import ProductOffer
from logger import log_structured
from bs4 import BeautifulSoup
import time
import urllib.parse

class PixelatoyScraper(AsyncScraperPlugin):
    """
    Async Scraper for Pixelatoy.
    Strategy: User provided Magic URL to fetch all items.
    Target: https://www.pixelatoy.com/es/module/ambjolisearch/jolisearch?s=masters+&ajs_cat=309&order=product.price.asc&resultsPerPage=9999999
    """
    
    @property
    def name(self) -> str:
        return "Pixelatoy"

    @property
    def base_url(self) -> str:
        return "https://www.pixelatoy.com/es/module/ambjolisearch/jolisearch"

    async def search(self, query: str) -> list[ProductOffer]:
        start_time = time.time()
        products = []
        
        # Facet/Magic URL provided by user.
        # Note: The user provided url has hardcoded 's=masters+' and 'ajs_cat=309'.
        # We should probably respect that specificity if it's the "Category" the user wants.
        # Query param from 'search' method might be redundant if we use this fixed URL.
        # I'll use the fixed URL as the "Category Source".
        
        params = {
            "s": "masters ", # From user URL
            "ajs_cat": "309",
            "order": "product.price.asc",
            "resultsPerPage": "9999999"
        }
        
        status = "SUCCESS"
        
        try:
            html = await self.fetch(self.base_url, params=params)
            
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                # Pixelatoy uses PrestaShop-like structure or similar module
                # Selectors need to be inferred or generic. 
                # Identifying 'product-miniature' is standard in newer Presta.
                items = soup.select('.product-miniature')
                
                if not items:
                     # Fallback check for older themes?
                     items = soup.select('.ajax_block_product')
                
                if items:
                    seen_urls = set()
                    for item in items:
                        try:
                            # Title
                            title_elem = item.select_one('.product-title a') or item.select_one('.product-name')
                            if not title_elem: continue
                            
                            title = title_elem.get_text(strip=True)
                            link = title_elem.get('href')
                            
                            if link in seen_urls: continue
                            seen_urls.add(link)
                            
                            # Image
                            img_elem = item.select_one('.thumbnail-container img') or item.select_one('.product_img_link img')
                            image_url = None
                            if img_elem:
                                image_url = img_elem.get('data-src') or img_elem.get('src')
                            
                            # Price
                            price_elem = item.select_one('.product-price') or item.select_one('.price')
                            price_str = price_elem.get_text(strip=True) if price_elem else "0.00€"
                            
                            # Filter false positives if broadly scraping?
                            # User URL is specific 'ajs_cat=309' (likely MOTU), so heavy filtering might not be needed.
                            # But slight check doesn't hurt.
                            if "master" not in title.lower() and "motu" not in title.lower() and "skeletor" not in title.lower() and "he-man" not in title.lower():
                                # Loose filter
                                pass 

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
                        except Exception:
                            continue
                else:
                    status = "EMPTY"
            else:
                 status = "NO_HTML"

        except Exception as e:
            self.logger.error(f"Error scraping Pixelatoy: {e}")
            status = "ERROR"
            
        duration = time.time() - start_time
        log_structured("SCRAPE_END", self.name, items_found=len(products), duration_seconds=round(duration, 2), status=status)
        return products
