import asyncio
import json
import logging
import random
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PixelatoyEval")

OUTPUT_FILE = "data/pixelatoy_eval.json"
# Using the main MOTU category found in the snippet. 
# While snippet was a search result, this is the persistent category URL.
START_URL = "https://www.pixelatoy.com/es/309-masters-del-universo" 

def parse_html_item(item):
    """
    Parses a Pixelatoy product item (PrestaShop theme).
    Selectors based on user-provided HTML snippet.
    """
    try:
        # Title & Link: h3.product-title > a
        title_tag = item.select_one('h3.product-title a')
        if not title_tag:
            return None
        
        name = title_tag.get_text(strip=True)
        link = title_tag.get('href')
        
        # Price: span.product-price (has content="191" attribute)
        price_span = item.select_one('span.product-price')
        price_val = None
        
        if price_span:
            # 1. Try 'content' attribute (Best/Cleanest)
            # From snippet: <span class="product-price" content="191">191,00&nbsp;€</span>
            price_content = price_span.get('content')
            if price_content:
                try:
                    price_val = float(price_content)
                except ValueError:
                    pass
            
            # 2. Fallback to text
            if price_val is None:
                txt = price_span.get_text(strip=True).replace('€', '').replace(',', '.').replace('&nbsp;', '').strip()
                try:
                    price_val = float(txt)
                except ValueError:
                    pass
        
        if price_val is None:
            # Might be out of stock/sold out without price showing, or login required?
            # But snippet shows price even for "Agotado" (out of stock) items.
            return None

        # Availability
        # Snippet shows: <span class="badge badge-danger product-unavailable mt-2">...Agotado...</span>
        is_avl = True
        unavailable_badge = item.select_one('.product-unavailable')
        if unavailable_badge and "agotado" in unavailable_badge.get_text(strip=True).lower():
            is_avl = False
            
        # Image
        img_tag = item.select_one('div.thumbnail-container img')
        img_url = None
        if img_tag:
             # PrestaShop lazy loading often uses data-src
             img_url = img_tag.get('data-src') or img_tag.get('src')

        return {
            "product_name": name,
            "price": price_val,
            "currency": "EUR",
            "url": link,
            "shop_name": "Pixelatoy",
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
                    delay = random.uniform(3.0, 6.0)
                    logger.info(f"Sleeping {delay:.2f}s...")
                    await asyncio.sleep(delay)

                response = await page_browser.goto(current_url, timeout=60000, wait_until="domcontentloaded")
                
                if response.status == 404:
                    logger.warning("404 Encountered. Stopping.")
                    break

                # Wait for product grid
                try:
                    await page_browser.locator("article.product-miniature").first.wait_for(timeout=15000)
                except:
                    logger.warning("No products found (timeout). Stopping.")
                    break

                soup = BeautifulSoup(await page_browser.content(), 'html.parser')
                
                # Select items
                items = soup.select('article.product-miniature')
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
