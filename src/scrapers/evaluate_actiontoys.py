import asyncio
import json
import logging
import random
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ActionToysEval")

OUTPUT_FILE = "data/actiontoys_eval.json"
START_URL = "https://actiontoys.es/figuras-de-accion/masters-of-the-universe/origins/?count=48"

def parse_html_item(item):
    """
    Robust extraction logic based on verified headers and price details.
    """
    try:
        # Link
        a_tag = item.select_one('.product-image a') or item.select_one('a')
        if not a_tag: return None
        link = a_tag.get('href')
        
        # Title
        title_tag = item.select_one('.woocommerce-loop-product__title') or item.select_one('h2') or item.select_one('h3')
        name = title_tag.get_text(strip=True) if title_tag else a_tag.get_text(strip=True)
        
        # Price extraction (Priority: Sale Price via <ins> -> Standard Price via <bdi>)
        # Logic verified against snippet: sale items have <ins><bdi>...</bdi></ins>
        price_tag_ins = item.select_one('.price ins bdi')
        price_tag_bdi = item.select_one('.price bdi') # This finds the first one if no specific query
        
        raw_price_txt = None
        
        if price_tag_ins:
            raw_price_txt = price_tag_ins.get_text(strip=True)
            # logger.debug(f"  -> Found Sale Price: {raw_price_txt}")
        elif price_tag_bdi:
            # If standard product, or maybe just <span ...><bdi>...</bdi></span>
            # Note: If it's a sale, '.price bdi' might hit the <del> one first if we aren't careful?
            # actually soup.select_one returns the first descendant. 
            # In user snippet: <del> is before <ins>, so select_one('.price bdi') might return the deleted price!
            # So we MUST rely on the check above. If no <ins>, we assume it's a regular price.
            # But wait, what if we picked the <del> price in the elif? 
            # If there is <del> there usually IS <ins>. 
            # So if we are in this elif, it means NO <ins> was found. So likely no sale.
            raw_price_txt = price_tag_bdi.get_text(strip=True)
        else:
            # Last resort
            price_amount = item.select_one('.price .amount')
            if price_amount:
                raw_price_txt = price_amount.get_text(strip=True)
        
        if not raw_price_txt:
            return None
            
        # Clean price string
        # e.g. "22,49€" -> 22.49
        clean_price = raw_price_txt.replace('€', '').replace(',', '.').replace('&nbsp;', '').strip()
        try:
            price_val = float(clean_price)
        except ValueError:
            logger.warning(f"Could not parse price: {clean_price} for {name}")
            return None
        
        # Availability
        is_avl = True
        if item.select_one('.out-of-stock-badge'): 
            is_avl = False

        # Image
        img_tag = item.select_one('.product-image img')
        img_url = None
        if img_tag:
             img_url = img_tag.get('data-src') or img_tag.get('src') or img_tag.get('data-lazy-src')

        return {
            "product_name": name,
            "price": price_val,
            "currency": "EUR",
            "url": link,
            "shop_name": "ActionToys",
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
                # Anti-ban delay before request
                if page_num > 1:
                    delay = random.uniform(2.5, 5.5)
                    logger.info(f"Sleeping {delay:.2f}s to be polite...")
                    await asyncio.sleep(delay)

                response = await page_browser.goto(current_url, timeout=60000, wait_until="domcontentloaded")
                
                if response.status == 404:
                    logger.warning("404 Encountered. Stopping.")
                    break
                
                # Check soft 404s
                title = await page_browser.title()
                if "not found" in title.lower() or "no encontrada" in title.lower():
                    logger.warning("Page soft-404. Stopping.")
                    break
                
                # Wait for items to ensure JS render
                try:
                    await page_browser.locator("li.product").first.wait_for(timeout=10000)
                except:
                    logger.warning("No products found on page (timeout). Stopping or checking next?")
                    # If this happens on page 1, bad. If page 10, maybe just empty.
                    if page_num == 1:
                        logger.error("No items on Page 1! Check selectors.")
                        break

                content = await page_browser.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                items = soup.select('li.product')
                logger.info(f"   Items found: {len(items)}")
                
                page_results = 0
                for item in items:
                    data = parse_html_item(item)
                    if data:
                        results.append(data)
                        page_results += 1
                
                logger.info(f"   Parsed {page_results} items on page {page_num}.")
                
                # Dynamic Pagination
                next_button = soup.select_one('a.next.page-numbers')
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
