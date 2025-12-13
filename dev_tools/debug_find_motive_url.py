import requests
from bs4 import BeautifulSoup
import re

def find_motive_endpoint():
    # URL that definitely loads Motive
    url = "https://fantasiapersonajes.es/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    print("Fetching home page...")
    r = requests.get(url, headers=headers)
    
    # Dump all script src or content to find the API url
    soup = BeautifulSoup(r.text, 'html.parser')
    scripts = soup.find_all('script')
    
    print(f"Scanning {len(scripts)} scripts...")
    
    # 1. Look for 'motive' related JS files
    motive_js_url = None
    for s in scripts:
        if s.get('src') and 'motive' in s.get('src'):
            motive_js_url = s.get('src')
            print(f"Found Motive JS: {motive_js_url}")
            break
            
    # 2. If we found the JS, fetch IT and look for the endpoint inside
    if motive_js_url:
        if motive_js_url.startswith('//'):
            motive_js_url = "https:" + motive_js_url
        
        print(f"Fetching JS: {motive_js_url}")
        js_r = requests.get(motive_js_url, headers=headers)
        
        # Look for URLs inside the JS
        # Regex for https://...
        urls = re.findall(r'https?://[^\s"\']+', js_r.text)
        print("URLs found in JS:")
        unique_urls = set()
        for u in urls:
            if "motive" in u:
                unique_urls.add(u)
        
        for u in unique_urls:
            # Filter for likely API endpoints
            if "api" in u or "search" in u:
                print(f"POTENTIAL API: {u}")
            else:
                print(f" - {u}")
            
    else:
        print("Could not find Motive JS file in HTML.")
        
    # 3. Look for config object in main HTML
    # var motive_init = { ... "api_url": "..." }
    if "api_url" in r.text or "apiUrl" in r.text:
        print("Found 'api_url' in HTML source!")
        # Print context
        start = r.text.find("api_url")
        print(r.text[start-50:start+100])

if __name__ == "__main__":
    find_motive_endpoint()
