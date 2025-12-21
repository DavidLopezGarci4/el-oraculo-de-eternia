import httpx
from typing import List
from src.scrapers.base import BaseSpider, ScrapedOffer
from src.core.logger import logger
from bs4 import BeautifulSoup
import re

class FantasiaSpider(BaseSpider):
    """
    Spider for Fantasia Personajes (PrestaShop).
    """
    def __init__(self):
        super().__init__(shop_name="Fantasia Personajes")
        self.base_url = "https://fantasiapersonajes.es/buscar"

    async def search(self, query: str) -> List[ScrapedOffer]:
        results = []
        
        # Legacy "Gold Mine" Strategy: Enhanced Search with High Page Size
        # Instead of generic category crawl which might be blocked or complex to parse,
        # we found that searching for "Masters of the Universe" with high limit works best.
        if query.lower() == "auto":
            logger.info("🕸️ Fantasia: activating 'Open Floodgates' (Enhanced Search).")
            # We use the broadest term that covers 99% of items.
            queries = ["Masters of the Universe"] 
        else:
             queries = [query]
            
        seen_urls = set()
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            
            for q in queries:
                logger.info(f"🕸️ Fantasia: Searching for '{q}'...")
                page = 1
                
                while True:
                    await self._random_sleep(1.0, 3.0) # Human-like pause between pages
                    params = {
                        "controller": "search",
                        "s": q,
                        "order": "product.position.desc",
                        "resultsPerPage": "100", # Legacy trick to minimize pagination
                        "page": page
                    }
                    
                    try:
                        response = await client.get(self.base_url, params=params, headers=self._get_random_header())
                        
                        if response.status_code != 200:
                            logger.error(f"Fantasia API Error: {response.status_code}")
                            break
                            
                        html = response.text
                        soup = BeautifulSoup(html, 'html.parser')
                        items = soup.select('.product-miniature')
                        
                        if not items:
                            break # No items found on this page
                        
                        items_found_page = 0
                        for item in items:
                            offer = self._parse_item(item)
                            if offer and offer.url not in seen_urls:
                                results.append(offer)
                                seen_urls.add(offer.url)
                                items_found_page += 1
                        
                        # Pagination check
                        next_btn = soup.select_one('.next')
                        if not next_btn or items_found_page == 0:
                            break
                            
                        page += 1
                        if page > 20: break # Safety limit
                        
                    except Exception as e:
                        logger.error(f"Fantasia Scraping Error on '{q}': {e}")
                        break
        
        logger.info(f"✅ Fantasia: Found {len(results)} total items.")
        return results

    def _parse_item(self, item: BeautifulSoup) -> ScrapedOffer | None:
        try:
            title_elem = item.select_one('.product-title a')
            if not title_elem: return None
            
            name = title_elem.get_text(strip=True)
            link = title_elem.get('href')
            
            # Filter relevance mainly to avoid pure junk - REMOVED for "Open Gates" Strategy
            # valid_keywords = ["masters", "origins", "turtles", "skeletor", "he-man", "thundercats", "transformers", "snake men", "motu"]
            # if not any(k in name.lower() for k in valid_keywords):
            #     return None

            price_elem = item.select_one('.product-price') or item.select_one('.price')
            if not price_elem: return None
            
            price_str = price_elem.get_text(strip=True)
            price_val = self._clean_price(price_str)
            
            if price_val == 0.0: return None
            
            # Availability
            # Usually PrestaShop has local selectors for stock.
            # Assuming available if listed, unless it says "Out of stock"
            is_available = True
            availability = item.select_one('.product-availability')
            if availability and "agotado" in availability.get_text(strip=True).lower():
                is_available = False

            return ScrapedOffer(
                product_name=name,
                price=price_val,
                currency="EUR",
                url=str(link),
                shop_name=self.shop_name,
                is_available=is_available
            )
        except Exception as e:
            # logger.warning(f"Error parsing item: {e}")
            return None

    def _clean_price(self, price_str: str) -> float:
        try:
            # Remove currency symbol and replace comma with dot
            clean = re.sub(r'[^\d,]', '', price_str)
            clean = clean.replace(',', '.')
            return float(clean)
        except:
            return 0.0
