import asyncio
import json
import logging
import random
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FrikiversoEval")

OUTPUT_FILE = "data/frikiverso_eval.json"
# Using the Mattel brand page from the snippet
START_URL = "https://frikiverso.es/es/brand/62-mattel"

def parse_html_item(item):
    """
    Parses a Frikiverso product item.
    Selectors based on user-provided HTML snippet.
    """
    try:
        # Title & Link: h3.s_title_block > a
        title_tag = item.select_one('h3.s_title_block a')
        if not title_tag:
            return None
        
        name = title_tag.get_text(strip=True)
        link = title_tag.get('href')
        
        # Price: div.product-price-and-shipping span.price
        # Note: Snippet shows <span class="price " aria-label="Precio">25,54&nbsp;€</span>
        # It does NOT show a 'content' attribute in the snippet, so we parse text.
        price_val = None
        price_span = item.select_one('span.price')
        
        if price_span:
            # Clean text: "25,54 €" -> "25.54"
            txt = price_span.get_text(strip=True).replace('€', '').replace('&nbsp;', '').strip()
            # Replace european comma with dot
            txt = txt.replace(',', '.')
            try:
                price_val = float(txt)
            except ValueError:
                pass
        
        if price_val is None:
            return None

        # Availability
        # Snippet doesn't explicitly show "Out of Stock" badge structure in the examples, 
        # but usually PrestaShop has availability flags.
        # We will assume available unless we find an explicit "Agotado" indicator if present?
        # In snippet: <span class="st_sticker_text" title="NUEVO">NUEVO</span>
        # We'll default to True for now, as I don't see an explicit "unavailable" class in the snippet items.
        is_avl = True
            
        # Image
        # Snippet: <img data-src="..." class="front-image cate_pro_lazy" src="...">
        img_tag = item.select_one('img.front-image')
        img_url = None
        if img_tag:
             img_url = img_tag.get('data-src') or img_tag.get('src')

        return {
            "product_name": name,
            "price": price_val,
            "currency": "EUR",
            "url": link,
            "shop_name": "Frikiverso",
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
                    await page_browser.locator("article.js-product-miniature").first.wait_for(timeout=15000)
                except:
                    logger.warning("No products found (timeout). Stopping.")
                    break

                soup = BeautifulSoup(await page_browser.content(), 'html.parser')
                
                # Select items
                items = soup.select('article.js-product-miniature')
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
                
                # Pagination: a.next.page-link or similar
                # Snippet: <li class="page-item"><a rel="next" href="..." class="page-link next js-search-link" ...>
                next_button = soup.select_one('a.page-link.next')
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
