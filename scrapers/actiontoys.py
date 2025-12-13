from logger import log_structured
import time
import requests
from typing import List
from models import ProductOffer
from scrapers.interface import ScraperPlugin

class ActionToysScraper:
    def __init__(self):
        self._name = "ActionToys"
        self._base_url = "https://actiontoys.es/wp-json/wc/store/products"
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_active(self) -> bool:
        return True

    def search(self, query: str) -> List[ProductOffer]:
        start_time = time.time()
        log_structured("SCRAPE_START", self.name, query=query)
        
        params = {
            "search": query,
            "per_page": 50,
            "page": 1
        }
        
        products = []
        status = "SUCCESS"
        error_msg = None
        
        while True:
            try:
                r = requests.get(self._base_url, params=params, headers=self._headers, timeout=15)
                if r.status_code != 200:
                    status = "API_ERROR"
                    error_msg = f"Status {r.status_code}"
                    log_structured("API_ERROR", self.name, status_code=r.status_code)
                    break
                
                data = r.json()
                if not data: break # End of results
                
                for item in data:
                    try:
                        p = self._parse_item(item)
                        if p: products.append(p)
                    except Exception as e:
                        log_structured("PARSE_ERROR", self.name, error=str(e), item_sample=str(item)[:50])
                        continue
                
                # Pagination
                if len(data) < params['per_page']: break
                params['page'] += 1
                if params['page'] > 5: break # Safety limit
                
            except Exception as e:
                status = "CRITICAL_ERROR"
                error_msg = str(e)
                log_structured("CRITICAL_ERROR", self.name, error=str(e))
                break
                
        duration = time.time() - start_time
        log_structured("SCRAPE_END", self.name, 
                      items_found=len(products), 
                      duration_seconds=round(duration, 2),
                      status=status,
                      error=error_msg)
                      
        return products

    def _parse_item(self, item: dict) -> ProductOffer | None:
        name = item.get('name', 'Desconocido')
        
        # Filter logic (same as original)
        if "masters" not in name.lower() and "origins" not in name.lower():
            return None
            
        price_data = item.get('prices', {})
        # Price is usually in cents string or formatted
        # WC Store API usually returns raw prices in minor units or computed strings
        # Adjust based on observed API behavior in original_app.py:
        # "price_val = float(price_data.get('price', 0)) / 100.0"
        
        price_val = float(price_data.get('price', 0)) / 100.0
        
        images = item.get('images', [])
        img_src = images[0].get('src') if images else None
        link = item.get('permalink')
        
        return ProductOffer(
            name=name,
            price_val=price_val,
            currency="€",
            url=link,
            image_url=img_src,
            store_name=self.name
        )
