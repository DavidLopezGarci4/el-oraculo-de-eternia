
import requests
from bs4 import BeautifulSoup
import sys

URL = "https://www.actionfigure411.com/masters-of-the-universe/origins-checklist.php"

def debug_structure():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    print(f"Fetching {URL}...")
    try:
        resp = requests.get(URL, headers=headers, timeout=30)
        print(f"Status: {resp.status_code}")
    except Exception as e:
        print(f"Request failed: {e}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    
    print("\n--- H2 Analysis ---")
    h2s = soup.find_all("h2")
    print(f"Found {len(h2s)} H2 tags.")
    
    found_sections = 0
    
    for i, h2 in enumerate(h2s):
        # Logic from existing script
        strong_tag = h2.find("strong")
        if not strong_tag:
            print(f"[H2 #{i}] SKIPPED (No <strong>): '{h2.get_text(strip=True)}'")
            continue
            
        title = strong_tag.get_text(strip=True)
        print(f"\n[H2 #{i}] MATCHED Title: '{title}'")
        
        # Check table
        next_table = h2.find_next("table")
        if next_table:
            rows = next_table.find_all("tr")
            print(f"  -> Linked Table Rows: {len(rows)}")
            if rows:
                cols = rows[0].find_all(["th", "td"])
                print(f"  -> First Row Headers: {[c.get_text(strip=True) for c in cols]}")
            found_sections += 1
        else:
            print("  -> Table NOT FOUND via find_next('table')")

    print(f"\nTotal Sections Found by Logic: {found_sections}")

if __name__ == "__main__":
    debug_structure()
