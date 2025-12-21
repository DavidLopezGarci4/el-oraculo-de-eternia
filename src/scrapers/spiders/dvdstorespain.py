import httpx
import asyncio
from typing import List, Optional
from src.scrapers.base import BaseSpider, ScrapedOffer
from src.core.logger import logger
from bs4 import BeautifulSoup
import re

class DVDStoreSpainSpider(BaseSpider):
    """
    Spider for DVD Store Spain.
    Strategy: Broad Category Scan + Strict Filtering.
    Why: Standard search is blocked/broken and Faceted URLs are fragile.
    The 'Merchandising' category contains all figures (~2900 items).
    We iterate deep and filter strictly for MOTU items.
    """
    def __init__(self):
        super().__init__(shop_name="DVDStoreSpain")
        self.start_url = "https://dvdstorespain.es/es/257-merchandising-cine-series-y-videojuegos"
        self.positive_keywords = [
            "masters del universo", "masters of the universe", "motu", 
            "he-man", "skeletor", "hordak", "she-ra", "teela", "beast man", 
            "man-at-arms", "man at arms", "sorceress", "stratos", "buzz-off",
            "trap jaw", "tri-klops", "evil-lyn", "faker", "scareglow", "king grayskull",
            "snake mountain", "castle grayskull", "battle cat", "panthor",
            "moss man", "ram man", "mekaneck", "man-e-faces", "stinkor", "two bad",
            "spikor", "webstor", "jitsu", "clawful", "whiplash", "kobra khan",
            "leech", "mantenna", "grizzlor", "horde trooper", "king hssss",
            "tung lashor", "rattlor", "squeeze", "face off", "clamp champ", "snout spout",
            "roboto", "sy-klone", "rio blast", "rokkon", "stonedar", "extendar",
            "gwildor", "blade", "saurod", "flogg", "slush head", "optikk", "karatti",
            "hoove", "lizorr", "spinwit", "tuskador", "quakke", "butthead", "staghorn",
            "granamyr", "turgul", "zoar", "screeech", "shadow weaver", "scorpia",
            "sea hawk", "kowl", "loo-kee", "madame razz", "broom", "bowa",
            "glimmer", "angella", "castaspella", "frosta", "perfuma", "peekablue",
            "flutterina", "mermista", "netossa", "spinnerella", "double trouble",
            "starla", "tallstar", "jewelstar", "swift wind", "crystal falls",
            "fright zone", "eternia", "fright zone", "slime pit", "point dread", 
            "talon fighter", "attak trak", "bashasaurus", "battle ram", "dragon walker",
            "land shark", "laser bolt", "night stalker", "road ripper", "roton",
            "spydor", "strider", "wind raider", "jet sled"
        ]
        self.negative_keywords = ["dvd", "blu-ray", "bluray", "cd", "libros"]

    async def search(self, query: str) -> List[ScrapedOffer]:
        results = []
        seen_urls = set()
        
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "es-ES,es;q=0.9"
            }
            
            target_urls = [self.start_url]
            
            if query.lower() != "auto":
                 # If user asks for specific term, try standard search (it 404s often but logic is here)
                 target_urls = [f"https://dvdstorespain.es/es/busqueda?s={query}"]

            for i, START_URL in enumerate(target_urls):
                logger.info(f"�️ DVDStoreSpain: Starting scrape on {START_URL}")
                page = 1
                empty_pages_limit = 3
                empty_pages_consecutive = 0
                max_pages = 150 # Covers ~3600 items (2900 existing)
                
                while page <= max_pages: 
                    sep = "&" if "?" in START_URL else "?"
                    final_url = f"{START_URL}?page={page}" if page > 1 else START_URL
                    
                    if True: # Always log for debugging
                        logger.info(f"   📄 Scraping Page {page}...")
                    
                    try:
                        response = await client.get(final_url, headers=headers)
                        if response.status_code == 404:
                            logger.info("   ⚠️ 404 Reached (End of Pagination)")
                            break
                        if response.status_code != 200:
                            logger.error(f"   ❌ HTTP {response.status_code} on page {page}")
                            break
                        
                        soup = BeautifulSoup(response.text, 'html.parser')
                        items = soup.select('.product-miniature')
                        logger.info(f"   found {len(items)} items on page {page}")

                        if not items:
                            empty_pages_consecutive += 1
                            if empty_pages_consecutive >= empty_pages_limit:
                                logger.info("   ⚠️ Consecutive empty pages. Stopping.")
                                break
                        else:
                            empty_pages_consecutive = 0
                        
                        for item in items:
                            offer = self._parse_item(item)
                            if offer:
                                if offer.url not in seen_urls:
                                    # Keyword Filtering logic
                                    title_lower = offer.product_name.lower()
                                    
                                    # Negative Check
                                    if any(bad in title_lower for bad in self.negative_keywords):
                                        continue
                                        
                                    # Positive Check
                                    if any(k in title_lower for k in self.positive_keywords):
                                        results.append(offer)
                                        seen_urls.add(offer.url)
                        
                        # Pagination check (Next button) - Removed to be robust. 
                        # We rely on 404 or consecutive empty pages to stop.
                        # next_btn = soup.select_one('.next') ...

                        page += 1
                        await asyncio.sleep(0.1) # Fast iteration
                        
                    except Exception as e:
                        logger.error(f"   ❌ Error scraping {final_url}: {e}")
                        break
                        
        logger.info(f"✅ DVDStoreSpain: Found {len(results)} valid items.")
        return results

    def _parse_item(self, item: BeautifulSoup) -> Optional[ScrapedOffer]:
        try:
            # Title
            title_elem = item.select_one('.product-title a')
            if not title_elem: return None
            
            name = title_elem.get_text(strip=True)
            link = title_elem.get('href')
            
            # Price
            price_elem = item.select_one('.price') or item.select_one('.product-price')
            if not price_elem: return None # or 0.0
            
            price_str = price_elem.get_text(strip=True)
            price_val = self._clean_price(price_str)
            
            if price_val == 0: return None
            
            # Availability
            is_available = True
            
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
