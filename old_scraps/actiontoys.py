from scrapers.base import AsyncScraperPlugin
from models import ProductOffer
from logger import log_structured
import time
import urllib.parse

class ActionToysScraper(AsyncScraperPlugin):
    """
    Async Scraper for ActionToys using WooCommerce Public API.
    """
    
    @property
    def name(self) -> str:
        return "ActionToys"

    @property
    def base_url(self) -> str:
        return "https://actiontoys.es/wp-json/wc/store/products"

    async def search(self, query: str) -> list[ProductOffer]:
        start_time = time.time()
        log_structured("SCRAPE_START", self.name, query=query)
        
        params = {
            "search": query,
            "per_page": 50, # Get max reasonable items
            "page": 1
        }
        
        products = []
        status = "SUCCESS"
        error_msg = None
        
        while True:
            try:
                data = await self.fetch(self.base_url, params=params, is_json=True)
                
                if not data:
                    break # Error or empty
                    
                # API returns list if valid, or dict if error sometimes
                if isinstance(data, dict) and 'code' in data:
                     status = "API_ERROR"
                     error_msg = str(data)
                     break
                     
                if not isinstance(data, list) or len(data) == 0:
                    break # End of results
                
                for item in data:
                    try:
                        p = self._parse_item(item)
                        if p: products.append(p)
                    except Exception as e:
                        continue
                
                # Pagination
                if len(data) < params['per_page']: 
                    break # Less items than requested means last page
                    
                params['page'] += 1
                if params['page'] > 5: break # Safety limit for this specific store
                
            except Exception as e:
                status = "CRITICAL_ERROR"
                error_msg = str(e)
                log_structured("CRITICAL_ERROR", self.name, error=str(e))
                break
                
        duration = time.time() - start_time
        log_structured("SCRAPE_END", self.name, 
                      items_found=len(products), 
                      duration_seconds=round(duration, 2),
                      status=status)
                      
        return products

    def _parse_item(self, item: dict) -> ProductOffer | None:
        name = item.get('name', 'Desconocido')
        
        # Hard filter for MOTU relevance
        if "masters" not in name.lower() and "origins" not in name.lower():
            return None
            
        price_data = item.get('prices', {})
        # Price is in minor units (cents) in WC Store API usually, 
        # BUT original scraper divided by 100. Let's verify standard WC Store API V3.
        # Yes, prices -> price is usually string "1999" for 19.99 or similar.
        # Original code: float(price_data.get('price', 0)) / 100.0
        
        try:
            raw_price = float(price_data.get('price', 0))
            price_val = raw_price / 100.0
        except:
            price_val = 0.0
        
        images = item.get('images', [])
        img_src = images[0].get('src') if images else None
        link = item.get('permalink')
        
        return ProductOffer(
            name=name,
            price_val=price_val,
            currency="€",
            url=link,
            image_url=img_src,
            store_name=self.name,
            # Generate expected display price
            display_price=f"{price_val:.2f}€"
        )
