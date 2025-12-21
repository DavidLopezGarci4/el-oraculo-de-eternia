import asyncio
import json
import logging
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ActionToysEval")

OUTPUT_FILE = "data/actiontoys_eval.json"
BASE_URL = "https://actiontoys.es/figuras-de-accion/masters-of-the-universe/origins/"

def parse_html_item(item):
    """
    Logic copied from ActionToysSpider._parse_html_item
    """
    try:
        a_tag = item.select_one('.woocommerce-LoopProduct-link') or item.select_one('a')
        if not a_tag: return None
        
        link = a_tag.get('href')
        
        title_tag = item.select_one('.woocommerce-loop-product__title') or item.select_one('h2') or item.select_one('h3')
        name = title_tag.get_text(strip=True) if title_tag else a_tag.get_text(strip=True)
        
        price_tag = item.select_one('.price bdi')
        if not price_tag:
             price_tag = item.select_one('.price .amount')
        
        if not price_tag:
            return None
        
        price_txt = price_tag.get_text(strip=True).replace('€', '').replace(',', '.').replace('&nbsp;', '')
        try:
            price_val = float(price_txt)
        except:
            return None
        
        is_avl = True
        if item.select_one('.out-of-stock-badge'): is_avl = False

        img_tag = item.select_one('img')
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
        
        for page_num in range(1, 8): # 1 to 7
            if page_num == 1:
                url = f"{BASE_URL}?count=48"
            else:
                url = f"{BASE_URL}page/{page_num}/?count=48"
                
            logger.info(f"Crawling Page {page_num}: {url}")
            
            try:
                await page_browser.goto(url, timeout=60000, wait_until="domcontentloaded")
                
                # Check 404
                # Title often yields "Page not found"
                title = await page_browser.title()
                if "not found" in title.lower() or "no encontrada" in title.lower():
                    logger.warning("Page not found. Stopping.")
                    break
                
                # Wait for items
                try:
                    await page_browser.locator("li.product").first.wait_for(timeout=10000)
                except:
                    logger.warning("No products found on page (timeout).")
                    break
                
                content = await page_browser.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                items = soup.select('li.product')
                logger.info(f"   Found {len(items)} raw products.")
                
                page_results = 0
                for item in items:
                    data = parse_html_item(item)
                    if data:
                        results.append(data)
                        page_results += 1
                
                logger.info(f"   Parsed {page_results} valid items.")
                
            except Exception as e:
                logger.error(f"Failed page {page_num}: {e}")
                
        await browser.close()
        
    logger.info(f"Total Scraped: {len(results)}")
    
    # Save to JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"DONE. Scraped {len(results)} items. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
