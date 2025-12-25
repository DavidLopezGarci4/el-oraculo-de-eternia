
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
    
    print(f"Found {len(h2s)} H2 tags.")
    
    for i, h2 in enumerate(h2s):
        text = h2.get_text(strip=True)
        print(f"[H2 #{i}] Text: '{text}'")
        
        strong = h2.find("strong")
        if strong:
            print(f"   Has Strong: Yes ('{strong.get_text(strip=True)}')")
        else:
            print("   Has Strong: No")
            
        next_table = h2.find_next("table")
        if next_table:
            rows = next_table.find_all("tr")
            print(f"   Next Table Rows: {len(rows)}")
        else:
            print("   Next Table: None")

if __name__ == "__main__":
    debug_structure()
