from bs4 import BeautifulSoup
import os

KEYWORDS = {
    'price_selector': '.price',
    'sale_price_selector': '.price ins bdi',
    'regular_price_selector': '.price bdi', # This might pick up the del price if present and first
}

def parse_snippet():
    file_path = "data/snippet_actiontoys.html"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    products = soup.select("li.product")
    print(f"Found {len(products)} products.")

    for i, item in enumerate(products):
        print(f"\n--- Product {i+1} ---")
        
        # Title
        title_tag = item.select_one('.woocommerce-loop-product__title') or item.select_one('h2') or item.select_one('h3')
        title = title_tag.get_text(strip=True) if title_tag else "NO TITLE"
        print(f"Title: {title}")

        # Link
        a_tag = item.select_one('.product-image a') or item.select_one('a')
        link = a_tag.get('href') if a_tag else "NO LINK"
        print(f"Link: {link}")

        # Image
        img_tag = item.select_one('.product-image img')
        img_url = "NO IMAGE"
        if img_tag:
             img_url = img_tag.get('data-src') or img_tag.get('src') or img_tag.get('data-lazy-src')
        print(f"Image: {img_url}")

        # Price Logic Testing
        price_tag_ins = item.select_one('.price ins bdi')
        price_tag_all_bdi = item.select('.price bdi')
        
        print(f"Raw BDI tags found: {len(price_tag_all_bdi)}")
        for idx, bdi in enumerate(price_tag_all_bdi):
            print(f"  BDI[{idx}]: {bdi.get_text(strip=True)}")

        final_price = None
        
        # Proposed "Impeccable" Logic
        if price_tag_ins:
            final_price = price_tag_ins.get_text(strip=True)
            print("  -> Detected SALE price via <ins>")
        elif price_tag_all_bdi:
            # If no ins, detecting the regular price.
            # However, if there is a <del> but no <ins> (unlikely in valid HTML, but possible), we should be careful.
            # In standard WooCommerce, if there's a sale, there is <del> AND <ins>.
            # If no sale, just a single <bdi> (usually).
            # But wait, looking at user snippet:
            # <span class="price"><del...><bdi>...</bdi></del> <ins...><bdi>...</bdi></ins></span>
            # If I select '.price bdi' I get both.
            # If I select '.price > bdi' (direct child), maybe? No, they are nested in spans/del/ins.
            
            # Safe bet: If <ins> exists, take it. If not, take the last <bdi> ? Or the first?
            # If no sale: <span class="price"><span class="woocommerce-Price-amount..."><bdi>...</bdi></span></span>
            # In that case, only 1 bdi exists.
            
            # So: If multiple BDIs, and one is inside <ins>, take that. 
            # If multiple BDIs and NONE inside <ins>, that's weird for WC.
            # If single BDI, take it.
            
            final_price = price_tag_all_bdi[-1].get_text(strip=True) # Taking the last one seems safer if del is first?
            # But let's check if it's inside <del>
            parent = price_tag_all_bdi[-1].find_parent('del')
            if parent:
                print("  -> WARNING: Selected price is inside <del>!")
            else:
                print("  -> Selected price (assumed current)")
        
        if final_price:
            # Clean price
            cleaned = final_price.replace('€', '').replace(',', '.').replace('&nbsp;', '')
            print(f"Final Price: {cleaned}")
        else:
            print("Final Price: NOT FOUND")

        # Availability
        is_avl = True
        if item.select_one('.out-of-stock-badge'):
            is_avl = False
        print(f"Available: {is_avl}")

if __name__ == "__main__":
    parse_snippet()
