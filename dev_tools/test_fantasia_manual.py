from scrapers.fantasiapersonajes import FantasiaScraper
import json
import logging

import sys

# Configure basic logging to see output
logging.basicConfig(level=logging.INFO)

def test_manual():
    # Redirect stdout to file to capture all debugs
    sys.stdout = open("run_log.txt", "w", encoding="utf-8")
    
    scraper = FantasiaScraper()
    print("🔎 Searching for 'origins' in Fantasia Personajes...")
    results = scraper.search("masters of the universe origins")
    
    print(f"✅ Found {len(results)} items.")
    for i, p in enumerate(results[:5]): # Show first 5
        print(f"--- Item {i+1} ---")
        print(f"Title: {p.name}")
        print(f"Price: {p.display_price} ({p.price_val})")
        print(f"Link: {p.url}")
        print(f"Image: {p.image_url}")
        
    sys.stdout.close()

if __name__ == "__main__":
    test_manual()
