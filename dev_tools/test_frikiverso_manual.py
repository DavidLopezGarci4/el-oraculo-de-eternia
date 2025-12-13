import sys
import os
# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scrapers.frikiverso import FrikiversoScraper
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)

def test_manual():
    sys.stdout = open("frikiverso_log.txt", "w", encoding="utf-8")
    print("--- Testing Frikiverso Scraper ---")
    scraper = FrikiversoScraper()
    print(f"Scraper Name: {scraper.name}")
    
    print("🔎 Searching for 'origins'...")
    results = scraper.search("masters of the universe origins")
    
    print(f"✅ Found {len(results)} items.")
    for i, p in enumerate(results[:5]): # Show first 5
        print(f"--- Item {i+1} ---")
        print(f"Title: {p.name}")
        print(f"Price: {p.display_price} ({p.price_val})")
        print(f"Link: {p.url}")
        print(f"Image: {p.image_url}")

if __name__ == "__main__":
    test_manual()
