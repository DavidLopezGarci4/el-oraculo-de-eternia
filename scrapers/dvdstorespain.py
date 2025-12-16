from scrapers.base import AsyncScraperPlugin
from models import ProductOffer
from logger import log_structured
from bs4 import BeautifulSoup
import time
import urllib.parse

class DVDStoreSpainScraper(AsyncScraperPlugin):
    """
    Async Scraper for DVD Store Spain.
    Target: Multi-Pass Strategy (Mattel Brand + Figures Facet + Replicas Facet).
    Reason: Single source scraping misses items (e.g. valid items not tagged as 'Figures'). Combined sources yield max coverage.
    """
    
    @property
    def name(self) -> str:
        return "DVD Store Spain"

    @property
    def start_urls(self) -> list[str]:
        # Incremental Strategy Sources
        return [
            # 1. High Precision: Official Mattel Brand Page
            "https://dvdstorespain.es/es/brand/260-mattel",
            
            # 2. High Volume: "Figures" Facet (The 81 items source)
            "https://dvdstorespain.es/es/257-merchandising-cine-series-y-videojuegos?q=Tipo+de+Producto-Figuras",
            
            # 3. Potential Missing: "Replicas" Facet
            "https://dvdstorespain.es/es/257-merchandising-cine-series-y-videojuegos?q=Tipo+de+Producto-R%C3%A9plicas",
            
            # 4. SAFETY NET: Broad Merchandising Category (No Filters)
            # This catches items missing from facets.
            "https://dvdstorespain.es/es/257-merchandising-cine-series-y-videojuegos"
        ]

    # Deprecated single base_url logic
    @property
    def base_url(self) -> str:
        return self.start_urls[0]

    async def search(self, query: str) -> list[ProductOffer]:
        print(f"!!! DVDStoreSpainScraper MULTI-PASS SEARCH STARTED !!! Query: {query}")
        start_time = time.time()
        products = []
        seen_urls = set()
        
        for source_idx, source_url in enumerate(self.start_urls):
            self.logger.info(f"Starting Pass {source_idx+1}: {source_url}")
            max_pages = 50
            page = 1
            
            while page <= max_pages:
                # Handle Pagination URL construction safely
                sep = "&" if "?" in source_url else "?"
                if page == 1:
                    target_url = source_url
                else:
                    target_url = f"{source_url}{sep}page={page}"
                
                try:
                    html = await self.fetch(target_url)
                    if not html: break
                    
                    soup = BeautifulSoup(html, 'html.parser')
                    items = soup.select('.product-miniature')
                    
                    if not items:
                        break # End of this Source
                    
                    for item in items:
                        try:
                            title_elem = item.select_one('.product-title a')
                            if not title_elem: continue
                            
                            title = title_elem.get_text(strip=True)
                            link = title_elem.get('href')
                            
                            if link in seen_urls: continue
                            seen_urls.add(link)
                            
                            # POSITIVE FILTER: Only keep MOTU items
                            title_lower = title.lower()
                            keywords = [
                                "masters del universo", "masters of the universe", "motu", 
                                "he-man", "skeletor", "hordak", "she-ra", "teela", "beast man", 
                                "man-at-arms", "man at arms", "sorceress", "stratos", "buzz-off",
                                "trap jaw", "tri-klops", "evil-lyn", "faker", "scareglow", "king grayskull"
                            ]
                            if not any(k in title_lower for k in keywords):
                                continue
                            
                            # NEGATIVE FILTER
                            if "dvd" in title_lower or "blu-ray" in title_lower or "bluray" in title_lower or "cd" in title_lower:
                                continue
    
                            img_elem = item.select_one('.thumbnail-container img')
                            image_url = None
                            if img_elem:
                                image_url = img_elem.get('data-src') or img_elem.get('src')
                            
                            # Price Selector Refinement
                            # HTML use <span itemprop="price" class="price">
                            price_elem = item.select_one('.price')
                            if not price_elem:
                                 price_elem = item.select_one('[itemprop="price"]')
                            if not price_elem:
                                 price_elem = item.select_one('.product-price')
                            
                            price_str = price_elem.get_text(strip=True) if price_elem else "0.00€"
                            
                            # If price is 0, logging it might be useful, but for now just scrape it.
                            
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
                            # new_in_pass += 1
                            
                        except Exception as item_e:
                            self.logger.error(f"Error processing item from {target_url}: {item_e}")
                            continue
                            
                    # Do NOT break if new_items_count == 0, because the page might just have other Mattel brands.
                    # Only break if the page itself was empty (handled above).
                    # if new_items_count == 0:
                    #    break

                    # Pagination: Ignore buttons, just go next until empty page/404 handling above.
                    page += 1
                    
                except Exception as e:
                    self.logger.error(f"Error scraping DVDStorePage {page} for source {source_url}: {e}")
                    break
                    
        duration = time.time() - start_time
        log_structured("SCRAPE_END", self.name, items_found=len(products), duration_seconds=round(duration, 2))
        return products
                

