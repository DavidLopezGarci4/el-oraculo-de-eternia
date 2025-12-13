import requests
from bs4 import BeautifulSoup
import re

def analyze_frikiverso():
    url = "https://frikiverso.es/es/buscar?controller=search&s=masters+of+the+universe+origins"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    print("1. Checking Standard Search URL...")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        if "product-miniature" in r.text:
            soup = BeautifulSoup(r.text, 'html.parser')
            items = soup.select('.product-miniature')
            print(f"Found {len(items)} items using standard PrestaShop selectors.")
        else:
            print("Standard selectors NOT found immediately.")
            
        print("\n2. Checking for Motive Commerce Scripts...")
        if "motive" in r.text.lower():
            print("HIT: 'motive' found in HTML source.")
            match = re.search(r'["\']?xEngineId["\']?:\s*["\']([a-zA-Z0-9_\-]+)["\']', r.text)
            if match:
                print(f"HIT: Found xEngineId: {match.group(1)}")
            else:
                print("Could not extract xEngineId via regex.")
        else:
            print("Motive NOT explicitly found in HTML source.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_frikiverso()
