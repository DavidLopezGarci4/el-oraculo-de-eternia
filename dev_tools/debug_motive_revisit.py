import requests
from bs4 import BeautifulSoup
import json
import re

# User provided URL: 
# https://fantasiapersonajes.es/?filter=brand%3AMATTEL&mot_p=2&mot_q=masters%20of%20the%20universe%20origins&sort=price%20asc
# This implies the site uses query params to trigger Motive.

def probe_motive():
    # 1. Try to hit the endpoint directly if we can guess it, 
    # OR hit the page and look for the configuration.
    
    url = "https://fantasiapersonajes.es/"
    params = {
        "filter": "brand:MATTEL",
        "mot_q": "masters of the universe origins",
        "mot_p": 1, # Start with page 1
        "sort": "price asc"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }
    
    print(f"Fetching URL: {url} with params...")
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Check standard containers
        items = soup.select('.product-miniature')
        print(f"Found {len(items)} items using standard selectors on Filter URL.")
        
        # Look for Motive specific scripts or data
        scripts = soup.find_all('script')
        for s in scripts:
            if s.string and "motive" in s.string.lower():
                print("\n--- Found Motive Script ---")
                print(s.string[:200] + "...")
                # Try to extract config
                if "xEngineId" in s.string:
                    print("HIT: Found xEngineId!")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    probe_motive()
