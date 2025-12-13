import requests
from bs4 import BeautifulSoup
from scrapers.interface import ScraperPlugin
from models import ProductOffer
from logger import log_structured
import datetime
import time
import random

class FantasiaScraper(ScraperPlugin):
    """
    Scraper para Fantasia Personajes usando el buscador estándar de PrestaShop.
    """
    
    def search(self, query: str) -> list[ProductOffer]:
        start_time = datetime.datetime.now()
        # Manual URL construction to ensure compatibility
        safe_query = query.replace(" ", "+")
        url = f"https://fantasiapersonajes.es/buscar?controller=search&s={safe_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
        }
        
        log_structured("scrape_start", {"store": "FantasiaPersonajes", "url": url, "query": query})
        products = []
        seen_urls = set()
        
        # Pagination loop (limit 15 pages to be safe, ~180 items max)
        for page in range(1, 16):
            if page > 1:
                # Be polite to the server
                time.sleep(random.uniform(1.0, 2.0))
                url_with_page = f"{url}&page={page}"
            else:
                url_with_page = url
            
            log_structured("scrape_page", {"store": "FantasiaPersonajes", "page": page, "url": url_with_page})
            
            try:
                r = requests.get(url_with_page, headers=headers, timeout=20)
                
                soup = BeautifulSoup(r.text, 'html.parser')
                items = soup.select('.product-miniature')
                
                if not items:
                    # No more items found, stop pagination
                    break
                
                page_new_items = 0
                for item in items:
                    try:
                        # Title & Link
                        title_elem = item.select_one('.product-title a')
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        link = title_elem.get('href')
                        
                        # Dedup check
                        if link in seen_urls:
                            continue
                        seen_urls.add(link)
                        
                        # Image (Lazy load handling)
                        img_elem = item.select_one('.thumbnail-container img')
                        image_url = None
                        if img_elem:
                            image_url = img_elem.get('data-src') or img_elem.get('src')
                            
                        # Price
                        price_elem = item.select_one('.product-price') or item.select_one('.product-price-and-shipping .price') or item.select_one('.price')
                        price_str = "0.00€"
                        price_val = 0.0
                        
                        if price_elem:
                            price_str = price_elem.get_text(strip=True)
                            # Clean price string
                            clean_price = price_str.replace('€', '').replace('.', '').replace(',', '.').strip()
                            try:
                                price_val = float(clean_price)
                            except ValueError:
                                price_val = 0.0
                                
                        offer = ProductOffer(
                            name=title,
                            price_val=price_val,
                            currency="€",
                            url=link,
                            image_url=image_url,
                            store_name="Fantasia Personajes",
                            display_price=price_str
                        )
                        products.append(offer)
                        page_new_items += 1
                        
                    except Exception as e:
                        continue
                
                if page_new_items == 0:
                    # Found items containers but all were duplicates or invalid?
                    break
                    
            except Exception as e:
                log_structured("scrape_error_page", {"store": "FantasiaPersonajes", "page": page, "error": str(e)})
                break
            
        duration = (datetime.datetime.now() - start_time).total_seconds()
        log_structured("scrape_complete", {"store": "FantasiaPersonajes", "count": len(products), "duration": duration})
        
        return products
