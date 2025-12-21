import httpx
from typing import List, Optional
from src.scrapers.base import BaseSpider, ScrapedOffer
from src.core.logger import logger
from bs4 import BeautifulSoup
import re

class PixelatoySpider(BaseSpider):
    """
    Spider for Pixelatoy.
    Uses 'ambjolisearch' module for efficient retrieval.
    """
    def __init__(self):
        super().__init__(shop_name="Pixelatoy")
        self.base_url = "https://www.pixelatoy.com/es/module/ambjolisearch/jolisearch"
        # Magic Category ID for MOTU seems to be 309 based on legacy code.
        self.cat_id = "309" 

    async def search(self, query: str) -> List[ScrapedOffer]:
        results = []
        seen_urls = set()
        
        # Legacy "Gold Mine" Magic URL: Fetch full catalog in one go
        logger.info("🕸️ Pixelatoy: activating 'Open Floodgates' (Magic JoliSearch URL).")
        
        params = {
            "s": "masters ", # Broad query required by JoliSearch
            "ajs_cat": "309", # MOTU Category ID
            "order": "product.price.asc",
            "resultsPerPage": "9999", # The magic key (Legacy used 9999999, using 9999 to be safe/sane)
            "page": "1"
        }
        
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            
            try:
                # Add delay before the big request
                await self._random_sleep(2.0, 5.0) 
                response = await client.get(self.base_url, params=params, headers=self._get_random_header())
                if response.status_code != 200:
                    logger.error(f"Pixelatoy Error: {response.status_code}")
                    return []
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Selectors (PrestaShop variants)
                items = soup.select('.product-miniature')
                if not items:
                     items = soup.select('.ajax_block_product')
                
                logger.info(f"✅ Pixelatoy: Magic URL returned {len(items)} items.")
                
                for item in items:
                    offer = self._parse_item(item)
                    if offer and offer.url not in seen_urls:
                        results.append(offer)
                        seen_urls.add(offer.url)

            except Exception as e:
                logger.error(f"Pixelatoy Magic Search Failed: {e}")
        
        return results

    def _parse_item(self, item: BeautifulSoup) -> Optional[ScrapedOffer]:
        try:
            # Title
            title_elem = item.select_one('.product-title a') or item.select_one('.product-name')
            if not title_elem: 
                logger.warning(f"Missing Title Elem. Content: {item.prettify()[:100]}")
                return None
            
            name = title_elem.get_text(strip=True)
            link = title_elem.get('href')
            
            # Price
            price_elem = item.select_one('.product-price') or item.select_one('.price')
            if not price_elem: 
                # logger.debug(f"Missing Price Elem for {name}")
                return None
                
            price_str = price_elem.get_text(strip=True)
            price_val = self._clean_price(price_str)
            
            # logger.info(f"Parsed: {name} | {price_str} -> {price_val}")
            
            if price_val == 0: 
                # logger.warning(f"Price 0 for {name}")
                return None
            
            # Availability
            is_available = True
            # Check for "Agotado" flags or buttons
            # .product-availability or .availability
            avail_elem = item.select_one('.product-availability')
            if avail_elem and ("agotado" in avail_elem.get_text(strip=True).lower() or "out of stock" in avail_elem.get_text(strip=True).lower()):
                is_available = False
                
            # If price is valid, usually listed.
            
            return ScrapedOffer(
                product_name=name,
                price=price_val,
                currency="EUR",
                url=str(link),
                shop_name=self.shop_name,
                is_available=is_available
            )
            
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None

    def _clean_price(self, price_str: str) -> float:
        try:
            clean = re.sub(r'[^\d,]', '', price_str)
            clean = clean.replace(',', '.')
            return float(clean)
        except:
            return 0.0
