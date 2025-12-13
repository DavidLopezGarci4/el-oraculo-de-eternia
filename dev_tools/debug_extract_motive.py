import requests
from bs4 import BeautifulSoup
import re
import json

def extract_and_test():
    url = "https://fantasiapersonajes.es/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    print("Fetching home page to find Engine ID...")
    r = requests.get(url, headers=headers)
    
    # Regex to find xEngineId: "xEngineId":"..." or similar js var
    # Pattern seen in other Motive integrations: var motive_init = { ... "engine_id": "..." }
    # or inside the motive html attribute.
    
    # Looking for the script content printed in previous step
    # "xEngineId"
    
    match = re.search(r'["\']?xEngineId["\']?:\s*["\']([a-zA-Z0-9_\-]+)["\']', r.text)
    if not match:
        # Try alternate pattern
        match = re.search(r'engine_id["\']?:\s*["\']([a-zA-Z0-9_\-]+)["\']', r.text)
        
    if match:
        engine_id = match.group(1)
        print(f"FAILED TO FIND ? No, FOUND Engine ID: {engine_id}")
        
        # Try constructing an API call
        # Endpoint often: https://api.motivecommerce.com/v1/search
        # Payload usually requires query and engine_id
        
        api_url = "https://api.motivecommerce.com/v1/search" 
        # Note: Exact endpoint might vary, could be "search.motive.co"
        
        payload = {
            "query": "masters of the universe origins",
            "page": 1,
            "limit": 20,
            "engine_id": engine_id
        }
        
        print(f"Attempting API call to {api_url}...")
        try:
            api_r = requests.post(api_url, json=payload, headers=headers)
            print(f"API Status: {api_r.status_code}")
            print(f"API Response: {api_r.text[:200]}")
        except Exception as e:
            print(f"API Error: {e}")
            
    else:
        print("Could not extract Engine ID via Regex. dumping script context:")
        soup = BeautifulSoup(r.text, 'html.parser')
        for s in soup.find_all('script'):
            if "xEngineId" in str(s):
                print(str(s)[:500])

if __name__ == "__main__":
    extract_and_test()
