import httpx
from typing import List, Optional
from src.scrapers.base import BaseSpider, ScrapedOffer
from src.core.logger import logger
from bs4 import BeautifulSoup
import re

class ElectropolisSpider(BaseSpider):
    """
    Spider for Electropolis (Magento).
    """
    def __init__(self):
        super().__init__(shop_name="Electropolis")
        self.base_url = "https://www.electropolis.es/zona-freaky/figuras/figuras.html"
        self.search_url = "https://www.electropolis.es/catalogsearch/result/"
        
        # Magic Filters for MOTU
        self.licencia = "99325" # Masters del Universo
        self.marcas = "92264"   # Mattel

    async def search(self, query: str) -> List[ScrapedOffer]:
        results = []
        seen_urls = set()
        
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            # Use randomized headers from BaseSpider
            # headers = self._get_random_header() # We will call it per request/page to rotate if needed, or once per session.
            # Let's rotate per session to be consistent, or per page? 
            # Per page is safer.
            pass # Placeholder, logic below
            
            # Determine Strategy
            # Use Legacy "Gold Mine" Params for Precise Filtering
            if query.lower() == "auto":
                logger.info("🕸️ Electropolis: Running AUTO mode (Magic Filters).")
                start_url = self.base_url
                base_params = {
                    "licencia": self.licencia,
                    "marcas": self.marcas,
                    "product_list_dir": "asc",
                    "product_list_limit": "30" # Standard limit
                }
            else:
                logger.info(f"🕸️ Electropolis: Searching for '{query}'...")
                start_url = self.search_url
                base_params = {"q": query}
            
            page = 1
            while True:
                params = base_params.copy()
                if page > 1:
                    params["p"] = page
                    
                logger.info(f"🚀 Requesting Page {page}...")
                
                try:
                    await self._random_sleep(1.0, 3.0)
                    response = await client.get(start_url, params=params, headers=self._get_random_header())
                    if response.status_code != 200:
                        logger.error(f"Electropolis HTTP Error: {response.status_code}")
                        break
                        
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Selectors (Magento)
                    items = soup.select('.item.product.product-item')
                    
                    if not items:
                        logger.info("No items found on page.")
                        break
                        
                    new_items = 0
                    for item in items:
                        offer = self._parse_item(item)
                        if offer and offer.url not in seen_urls:
                            results.append(offer)
                            seen_urls.add(offer.url)
                            new_items += 1
                            
                    if new_items == 0:
                        break
                        
                    # Pagination
                    next_link = soup.select_one('.pages-item-next')
                    if not next_link:
                        break
                        
                    page += 1
                    if page > 20: break
                    
                except Exception as e:
                    logger.error(f"Error scraping Electropolis: {e}")
                    break
                    
        logger.info(f"✅ Electropolis: Found {len(results)} items.")
        return results

    def _parse_item(self, item: BeautifulSoup) -> Optional[ScrapedOffer]:
        try:
            # Title
            title_elem = item.select_one('.product-item-link')
            if not title_elem: return None
            
            name = title_elem.get_text(strip=True)
            link = title_elem.get('href')
            
            # Price
            price_elem = item.select_one('.price')
            if not price_elem: return None
            price_str = price_elem.get_text(strip=True)
            price_val = self._clean_price(price_str)
            
            if price_val == 0: return None
            
            # Availability
            is_available = True
            # Check "stock unavailable" class or similar
            # Magento often uses .unavailable or .stock.unavailable
            stock_elem = item.select_one('.stock.unavailable')
            if stock_elem:
                is_available = False
                
            return ScrapedOffer(
                product_name=name,
                price=price_val,
                currency="EUR",
                url=str(link),
                shop_name=self.shop_name,
                is_available=is_available
            )
            
        except Exception:
            return None

    def _clean_price(self, price_str: str) -> float:
        try:
            clean = re.sub(r'[^\d,]', '', price_str)
            clean = clean.replace(',', '.')
            return float(clean)
        except:
            return 0.0
