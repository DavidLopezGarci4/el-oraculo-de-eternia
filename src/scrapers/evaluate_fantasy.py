import asyncio
import json
import logging
import random
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FantasyEval")

OUTPUT_FILE = "data/fantasy_eval.json"
START_URL = "https://fantasiapersonajes.es/3380-motu-origins"

def parse_html_item(item):
    """
    Parses a PrestaShop product item.
    Selectors provided by user + standard PrestaShop structure.
    """
    try:
        # Title & Link
        title_tag = item.select_one('h2.product-title a')
        if not title_tag:
            return None
        
        name = title_tag.get_text(strip=True)
        link = title_tag.get('href')
        
        # Price
        # User specified: span.product-price attribute "content"
        price_span = item.select_one('span.product-price')
        price_val = None
        
        if price_span:
            # Try content attribute first (cleanest)
            price_content = price_span.get('content')
            if price_content:
                try:
                    price_val = float(price_content)
                except ValueError:
                    pass
            
            # Fallback to text if content is missing/invalid
            if price_val is None:
                txt = price_span.get_text(strip=True).replace('€', '').replace(',', '.').replace('&nbsp;', '').strip()
                try:
                    price_val = float(txt)
                except ValueError:
                    pass
        
        if price_val is None:
            return None

        # Availability
        # PrestaShop usually has a 'product-availability' block or specific classes like 'available' / 'unavailable'
        # defaulting to True for now unless we see explicit "out of stock" indicators common in PS.
        # User didn't specify out of stock selector, so we'll be optimistic or check for generic text.
        is_avl = True
        
        # Image
        img_tag = item.select_one('div.thumbnail-container img') or item.select_one('img')
        img_url = None
        if img_tag:
             img_url = img_tag.get('data-src') or img_tag.get('src')

        return {
            "product_name": name,
            "price": price_val,
            "currency": "EUR",
            "url": link,
            "shop_name": "Fantasia Personajes",
            "is_available": is_avl,
            "image_url": img_url
        }
    except Exception as e:
        logger.error(f"Error parsing item: {e}")
        return None

async def main():
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page_browser = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        current_url = START_URL
        page_num = 1
        
        while current_url:
            logger.info(f"Crawling Page {page_num}: {current_url}")
            
            try:
                # Anti-ban delay
                if page_num > 1:
                    delay = random.uniform(2.5, 5.5)
                    logger.info(f"Sleeping {delay:.2f}s...")
                    await asyncio.sleep(delay)

                response = await page_browser.goto(current_url, timeout=60000, wait_until="domcontentloaded")
                
                # PrestaShop soft 404 check?
                # Usually standard 404 works, but let's be safe
                if response.status == 404:
                    logger.warning("404 Encountered. Stopping.")
                    break
                
                # Check for "There are no products" message common in PS
                content = await page_browser.content()
                if "No hay productos" in content or "no products" in content.lower():
                     # BUT wait, this text might appear in search bars etc. 
                     # Better to trust the selector count.
                     pass

                # Wait for products
                try:
                    # User said: article.product-miniature or div.js-product-miniature-wrapper
                    await page_browser.locator("article.product-miniature, div.js-product-miniature-wrapper").first.wait_for(timeout=10000)
                except:
                    logger.warning("No products found (timeout). Stopping.")
                    break

                soup = BeautifulSoup(await page_browser.content(), 'html.parser')
                
                # Select items
                items = soup.select('article.product-miniature')
                if not items:
                    items = soup.select('div.js-product-miniature-wrapper')
                
                logger.info(f"   Items found: {len(items)}")
                
                if not items:
                    break

                page_results = 0
                for item in items:
                    data = parse_html_item(item)
                    if data:
                        results.append(data)
                        page_results += 1
                
                logger.info(f"   Parsed {page_results} items on page {page_num}.")
                
                # Pagination: nav.pagination a.next
                # User note: "Mostrando 1-28 de 28" means no next page.
                # If there IS a next page, it's usually inside <nav class="pagination"> ... <a class="next ...">
                next_button = soup.select_one('nav.pagination a.next')
                if next_button:
                    next_href = next_button.get('href')
                    logger.info(f"   Next page detected: {next_href}")
                    current_url = next_href
                    page_num += 1
                else:
                    logger.info("   No 'Next' button found. Crawl finished.")
                    current_url = None
                    
            except Exception as e:
                logger.error(f"Critical error on page {page_num}: {e}")
                break
                
        await browser.close()
        
    logger.info(f"Total Scraped: {len(results)}")
    
    # Save to JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"DONE. Scraped {len(results)} items. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
