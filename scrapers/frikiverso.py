import requests
from bs4 import BeautifulSoup
from scrapers.interface import ScraperPlugin
from models import ProductOffer
from logger import log_structured
import datetime
import time
import random

class FrikiversoScraper(ScraperPlugin):
    """
    Scraper para Frikiverso usando el buscador estándar de PrestaShop.
    """
    name = "Frikiverso"
    
    def search(self, query: str) -> list[ProductOffer]:
        start_time = datetime.datetime.now()
        # Frikiverso search URL pattern
        # https://frikiverso.es/es/buscar?controller=search&s=...
        safe_query = query.replace(" ", "+")
        base_url = f"https://frikiverso.es/es/buscar?controller=search&s={safe_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
        }
        
        log_structured("scrape_start", {"store": "Frikiverso", "url": base_url, "query": query})
        products = []
        seen_urls = set()
        
        # Pagination loop (limit 10 pages)
        for page in range(1, 11):
            if page > 1:
                time.sleep(random.uniform(1.0, 2.0))
                url = f"{base_url}&page={page}"
            else:
                url = base_url
            
            try:
                r = requests.get(url, headers=headers, timeout=20)
                soup = BeautifulSoup(r.text, 'html.parser')
                items = soup.select('.js-product-miniature')
                
                if not items:
                    break
                
                page_new_items = 0
                for item in items:
                    try:
                        # Title
                        title_elem = item.select_one('.s_title_block a')
                        if not title_elem:
                            continue
                        title = title_elem.get_text(strip=True)
                        link = title_elem.get('href')
                        
                        if link in seen_urls:
                            continue
                        seen_urls.add(link)
                        
                        # Image
                        img_elem = item.select_one('.front-image')
                        image_url = None
                        if img_elem:
                            image_url = img_elem.get('data-src') or img_elem.get('src')
                            
                        # Price
                        price_elem = item.select_one('.product-price-and-shipping .price')
                        price_str = "0.00€"
                        price_val = 0.0
                        if price_elem:
                            price_str = price_elem.get_text(strip=True)
                            clean_price = price_str.replace('€', '').replace('.', '').replace(',', '.').strip()
                            try:
                                price_val = float(clean_price)
                            except:
                                price_val = 0.0
                                
                        offer = ProductOffer(
                            name=title,
                            price_val=price_val,
                            currency="€",
                            url=link,
                            image_url=image_url,
                            store_name="Frikiverso",
                            display_price=price_str
                        )
                        products.append(offer)
                        page_new_items += 1
                        
                    except Exception:
                        continue
                
                if page_new_items == 0:
                    break
                    
            except Exception as e:
                log_structured("scrape_error_page", {"store": "Frikiverso", "page": page, "error": str(e)})
                break
                
        duration = (datetime.datetime.now() - start_time).total_seconds()
        log_structured("scrape_complete", {"store": "Frikiverso", "count": len(products), "duration": duration})
        return products
