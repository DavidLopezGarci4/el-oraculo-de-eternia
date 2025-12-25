
import requests
from bs4 import BeautifulSoup

URL = "https://www.actionfigure411.com/masters-of-the-universe/origins-checklist.php"

def debug_siblings():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    print(f"Fetching {URL}...")
    resp = requests.get(URL, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Find the specific H2
    h2s = soup.find_all("h2")
    if not h2s: 
        print("No H2 found")
        return

    # Check the first H2 (Origins)
    target_h2 = h2s[0]
    print(f"Target H2: {target_h2.get_text(strip=True)}")
    
    curr = target_h2.next_sibling
    count = 0
    while curr and count < 50:
        if curr.name:
            text_content = curr.get_text(strip=True)[:50]
            print(f"Sibling [{count}]: <{curr.name}> (attrs: {curr.attrs}) Text: '{text_content}'")
            if curr.name == "h2":
                print("-> Reached next H2. Stopping.")
                break
            if curr.name == "table":
                rows = curr.find_all("tr")
                print(f"   -> Table with {len(rows)} rows.")
        # else: ignore text nodes for cleaner output
        curr = curr.next_sibling
        if curr and curr.name: count += 1 # Only incr on tags

if __name__ == "__main__":
    debug_siblings()
