import requests
from bs4 import BeautifulSoup
import re
import json

def get_engine_id():
    url = "https://fantasiapersonajes.es/"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    match = re.search(r'["\']?xEngineId["\']?:\s*["\']([a-zA-Z0-9_\-]+)["\']', r.text)
    if match:
        return match.group(1)
    return None

def brute_force():
    engine_id = get_engine_id()
    if not engine_id:
        print("CRITICAL: Could not find Engine ID")
        return

    print(f"Targeting Engine ID: {engine_id}")
    
    endpoints = [
        "https://api.motivecommerce.com/v1/search",
        "https://api.motive.co/v1/search",
        "https://api.empathy.co/search/v1/query",
        "https://api.empathybroker.com/search/v1/query",
        "https://api.empathybroker.com/search/v1/query/{engine_id}",
        "https://api-motive.empathy.co/search/v1/query"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://fantasiapersonajes.es",
        "Referer": "https://fantasiapersonajes.es/"
    }
    
    # Try different payloads. Motive/Empathy usually requires q, rows, start/page.
    payloads = [
        {"query": "masters", "rows": 1, "start": 0, "engine_id": engine_id}, # Generic
        {"q": "masters", "rows": 1, "start": 0, "__env": "mobile"}, # Empathy style
    ]
    
    for url in endpoints:
        print(f"--- Testing {url} ---")
        for i, p in enumerate(payloads):
            try:
                # Some APIs use path param for engine ID
                # e.g. /search/v1/query/{engine_id}
                if "{engine_id}" in url:
                    final_url = url.format(engine_id=engine_id)
                else:
                    final_url = url
                
                # Try JSON POST
                r = requests.post(final_url, json=p, headers=headers, timeout=5)
                print(f"POST (Payload {i}) Status: {r.status_code}")
                if r.status_code == 200:
                    print("SUCCESS! Response snippet:")
                    print(r.text[:200])
                    return
                
                # Try GET
                r = requests.get(final_url, params=p, headers=headers, timeout=5)
                print(f"GET (Payload {i}) Status: {r.status_code}")
                if r.status_code == 200:
                    print("SUCCESS! Response snippet:")
                    print(r.text[:200])
                    return
                    
            except Exception as e:
                print(f"Failed: {e}")

if __name__ == "__main__":
    brute_force()
