import asyncio
import random
import json
import logging
import sys
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("electropolis_eval.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Target URL (Zone Freak seems appropriate based on snippet)
BASE_URL = "https://www.electropolis.es/zona-freaky.html"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        all_products = []
        current_url = BASE_URL
        
        # Limit pages for evaluation
        MAX_PAGES = 3

        for page_num in range(1, MAX_PAGES + 1):
            logger.info(f"Crawling Page {page_num}: {current_url}")
            
            try:
                await page.goto(current_url, timeout=60000, wait_until="domcontentloaded")
                
                # Random delay to be polite
                await asyncio.sleep(random.uniform(2.0, 4.0))

                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Magento 2 usually uses .product-item or .product-item-info
                # Based on snippet: <div class="product-item-info" ...>
                items = soup.select('.product-item-info')
                
                if not items:
                    logger.warning("No items found using .product-item-info selector.")
                    # Fallback to broader selector if needed
                    items = soup.select('li.product-item')

                logger.info(f"   Items found: {len(items)}")

                for item in items:
                    data = parse_html_item(item)
                    if data:
                        all_products.append(data)
                
                logger.info(f"   Parsed {len(items)} items on page {page_num}.")

                # Pagination
                # Magento standard: .pages .action.next or a.next
                next_btn = soup.select_one('.pages .action.next')
                if not next_btn:
                     next_btn = soup.select_one('a.next') # General fallback

                if next_btn and next_btn.get('href'):
                    next_link = next_btn.get('href')
                    logger.info(f"   Next page detected: {next_link}")
                    current_url = next_link
                else:
                    logger.info("   No 'Next' button found. Crawl finished.")
                    break

            except Exception as e:
                logger.error(f"Error on page {page_num}: {e}")
                break

        await browser.close()
        
        # Save Results
        with open('data/electropolis_eval.json', 'w', encoding='utf-8') as f:
            json.dump(all_products, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Total Scraped: {len(all_products)}")
        print(f"DONE. Scraped {len(all_products)} items. Saved to data/electropolis_eval.json")

def parse_html_item(item):
    try:
        # Name & Link
        # Snippet: <strong class="product name product-item-name"><a class="product-item-link" ...>
        name_tag = item.select_one('.product-item-name a')
        if not name_tag: return None
        
        name = name_tag.get_text(strip=True)
        link = name_tag.get('href')

        # Price
        # Snippet: <span data-price-amount="16.58" data-price-type="finalPrice" ...>
        # We look for the finalPrice attribute which is very reliable in Magento 2
        price_val = 0.0
        price_tag = item.select_one('[data-price-type="finalPrice"]')
        
        if price_tag and price_tag.has_attr('data-price-amount'):
            try:
                price_val = float(price_tag['data-price-amount'])
            except:
                pass
        else:
            # Fallback text parsing
             price_txt_tag = item.select_one('.price')
             if price_txt_tag:
                 txt = price_txt_tag.get_text(strip=True).replace('€','').replace(',','.').replace('&nbsp;','')
                 try:
                     price_val = float(txt)
                 except:
                     pass

        # Image
        # Snippet: <img class="product-image-photo" ... src="...">
        img_tag = item.select_one('img.product-image-photo')
        if not img_tag:
             # Look for any image inside product-image-wrapper
             img_tag = item.select_one('.product-image-wrapper img')
        
        img_url = None
        if img_tag:
            img_url = img_tag.get('src')
        
        # Availability
        # Magento usually has .stock.available or .stock.unavailable
        is_avl = True
        stock_status = item.select_one('.stock.unavailable')
        if stock_status:
            is_avl = False

        return {
            "product_name": name,
            "price": price_val,
            "currency": "EUR",
            "url": link,
            "shop_name": "Electropolis",
            "is_available": is_avl,
            "image_url": img_url
        }

    except Exception as e:
        # logger.error(f"Error parsing item: {e}") # Reduce data noise
        return None

if __name__ == "__main__":
    asyncio.run(run())
