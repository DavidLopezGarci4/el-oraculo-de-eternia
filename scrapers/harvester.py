import sys
import os
import json
import time
from playwright.sync_api import sync_playwright

# Ensure data directory exists
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)
SNAPSHOT_FILE = os.path.join(DATA_DIR, 'products_snapshot.json')

def scrape_fantasia(page):
    print("⚔️ Scraping Fantasia Personajes (Magic URL)...")
    # User provided 'resultsPerPage' trick
    url = "https://fantasiapersonajes.es/buscar?controller=search&s=masters+of+the+universe&order=product.position.desc&resultsPerPage=9999999"
    page.goto(url)
    page.wait_for_timeout(5000)
    
    # Try to find subcategory 'origins' if exists or just scroll parent
    # Checking if 404, if so fallback to search
    if "404" in page.title():
        print("   Category not found, falling back to Search...")
        page.goto("https://fantasiapersonajes.es/buscar?controller=search&s=masters+of+the+universe")
        page.wait_for_timeout(5000)

    # Infinite scroll / Load More
    # Press End key repeatedly
    for _ in range(20): 
        page.keyboard.press("End")
        page.wait_for_timeout(1000)
        
    items = page.locator(".product-miniature, .js-product-miniature").all()
    print(f"   Found {len(items)} items.")
    
    results = []
    seen = set()
    for item in items:
        try:
            # Correct selectors for Fantasia
            title = item.locator(".product-title a").inner_text()
            if title in seen: continue
            seen.add(title)

            link = item.locator(".product-title a").get_attribute("href")
            try:
                price_text = item.locator(".price").inner_text()
                price_val = float(price_text.replace("€", "").replace(",", ".").strip())
            except:
                price_val = 0.0
                price_text = "0.00€"
                
            img = item.locator("img").first.get_attribute("src")
            
            results.append({
                "name": title,
                "price_val": price_val,
                "display_price": price_text,
                "url": link,
                "image_url": img,
                "store_name": "Fantasia Personajes"
            })
        except Exception as e:
            continue
    return results

def scrape_frikiverso(page):
    print("⚔️ Scraping Frikiverso (Magic URL)...")
    # Using safer limit to avoid timeouts (500 is enough for 129 items)
    url = "https://frikiverso.es/es/buscar?controller=search&s=masters+of+the+universe&order=product.position.desc&resultsPerPage=500"
    try:
        page.goto(url, timeout=60000) # 60s timeout
    except:
        print("   ! Timeout loading page, trying to proceed anyway...")

    page.wait_for_timeout(5000)
    
    # Infinite scroll
    print("   Scrolling to load images...")
    for i in range(10): # Reduced from 20 to 10
        print(f"   Scroll {i+1}/10...", end="\r")
        page.keyboard.press("End")
        page.wait_for_timeout(1000)
    print("\n   Scroll done.")
        
    items = page.locator(".js-product-miniature").all() 
    print(f"   Found {len(items)} items.")
    
    results = []
    for item in items:
        try:
            # Frikiverso specific selectors
            if item.locator(".s_title_block a").count() > 0:
                title_el = item.locator(".s_title_block a")
                title = title_el.inner_text()
                link = title_el.get_attribute("href")
            else:
                continue

            try:
                price_text = item.locator(".price").first.inner_text()
                price_val = float(price_text.replace("€", "").replace(",", ".").strip())
            except:
                price_val = 0.0
                price_text = "0.00€"

            img = item.locator("img").first.get_attribute("src")
            
            results.append({
                "name": title,
                "price_val": price_val,
                "display_price": price_text,
                "url": link,
                "image_url": img,
                "store_name": "Frikiverso"
            })
        except:
            continue
    return results

def run_harvester():
    print("🚜 Starting Local Harvester...")
    all_products = []
    
    with sync_playwright() as p:
        # headless=False to avoid detection
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()
        
        try:
            items_fantasia = scrape_fantasia(page)
            all_products.extend(items_fantasia)
        except Exception as e:
            print(f"Error scraping Fantasia: {e}")
            
        try:
            items_frikiverso = scrape_frikiverso(page)
            all_products.extend(items_frikiverso)
        except Exception as e:
            print(f"Error scraping Frikiverso: {e}")
            
        browser.close()
        
    print(f"💾 Saving {len(all_products)} products to {SNAPSHOT_FILE}...")
    with open(SNAPSHOT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)
    print("✅ Done!")

if __name__ == "__main__":
    run_harvester()
