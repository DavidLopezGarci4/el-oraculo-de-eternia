import httpx
from typing import List, Optional
from src.scrapers.base import BaseSpider, ScrapedOffer
from src.core.logger import logger
from bs4 import BeautifulSoup
import re

class FrikiversoSpider(BaseSpider):
    """
    Spider for Frikiverso (PrestaShop).
    """
    def __init__(self):
        super().__init__(shop_name="Frikiverso")
        # Legacy "Gold Mine" URL: Faceted Search for MOTU + Mattel
        self.base_url = "https://frikiverso.es/es/149-figuras"
        self.facet_query = "Licencia-Masters+del+Universo/Marca-Mattel"

    async def search(self, query: str) -> List[ScrapedOffer]:
        results = []
        seen_urls = set()
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            
            # ALWAYS use the Broad Facet Strategy regardless of query
            logger.info("🕸️ Frikiverso: activating 'Open Floodgates' (Facet Strategy).")
            start_url = f"{self.base_url}?q={self.facet_query}"
            
            page = 1
            while True:
                await self._random_sleep(1.0, 3.0) # Human-like pause
                # Construct URL for pages
                if page == 1:
                    target_url = start_url
                else:
                    target_url = f"{start_url}&page={page}"
                    
                logger.info(f"📄 Scraping Page {page}: {target_url}")
                
                try:
                    response = await client.get(target_url, headers=self._get_random_header())
                    if response.status_code != 200:
                        logger.error(f"Frikiverso HTTP Error: {response.status_code}")
                        break
                        
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 1. Parse Items
                    items = soup.select('.js-product-miniature')
                    if not items:
                        logger.warning("No items found on this page.")
                        break
                        
                    new_items = 0
                    for item in items:
                        offer = self._parse_item(item)
                        if offer and offer.url not in seen_urls:
                            results.append(offer)
                            seen_urls.add(offer.url)
                            new_items += 1
                            
                    if new_items == 0:
                        logger.info("No new items found on page (duplicates?). Stopping.")
                        break
                        
                    # 2. Pagination Check
                    # Look for "next" button
                    next_btn = soup.select_one('.pagination .next')
                    # PrestaShop sometimes disables it by adding 'disabled' class
                    if not next_btn or 'disabled' in next_btn.get_attribute_list('class'):
                        break
                        
                    page += 1
                    if page > 50: # Safety
                        break
                        
                except Exception as e:
                    logger.error(f"Error requesting {target_url}: {e}")
                    break
                    
        logger.info(f"✅ Frikiverso: Found {len(results)} items.")
        return results

    def _parse_item(self, item: BeautifulSoup) -> Optional[ScrapedOffer]:
        try:
            # Title
            title_elem = item.select_one('.s_title_block a') or item.select_one('.product-title a')
            if not title_elem: return None
            
            name = title_elem.get_text(strip=True)
            link = title_elem.get('href')
            
            # Price
            price_elem = item.select_one('.product-price-and-shipping .price')
            if not price_elem: return None
            price_str = price_elem.get_text(strip=True)
            price_val = self._clean_price(price_str)
            
            if price_val == 0: return None
            
            # Availability (Check if "Buy" button is disabled or "Agotado" label)
            is_available = True
            # Often PrestaShop has availability flags
            # Look for explicit "Agotado"
            labels = item.select('.product-flag')
            for l in labels:
                if "agotado" in l.get_text(lower=True) or "out of stock" in l.get_text(lower=True):
                    is_available = False
            
            # Specific check for Frikiverso "unavailable-message"?
            # If price is valid, usually listed.
            
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
