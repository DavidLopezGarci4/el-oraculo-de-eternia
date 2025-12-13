import requests
from bs4 import BeautifulSoup

HEADERS_STATIC = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/"
}

def test_kidinn():
    print("Testing Kidinn (Static with Pro Headers)...")
    url = "https://www.tradeinn.com/kidinn/es/masters-of-the-universe/5883/nm"
    try:
        r = requests.get(url, headers=HEADERS_STATIC, timeout=15)
        print(f"Status Code: {r.status_code}")
        
        soup = BeautifulSoup(r.text, 'html.parser')
        items = soup.select('div.js-product-list-item')
        print(f"Kidinn Items found: {len(items)}")
        
        if len(items) == 0:
            print("Debugging HTML content (first 500 chars):")
            print(r.text[:500])
        else:
            print(f"First item: {items[0].get_text()[:50]}...")
    except Exception as e:
        print(f"Kidinn Failed: {e}")

def test_actiontoys():
    print("\nTesting ActionToys (Static with Pro Headers)...")
    url = "https://actiontoys.es/figuras-de-accion/masters-of-the-universe/"
    try:
        r = requests.get(url, headers=HEADERS_STATIC, timeout=15)
        print(f"Status Code: {r.status_code}")
        
        soup = BeautifulSoup(r.text, 'html.parser')
        items = soup.select('li.product, article.product-miniature, div.product-small')
        print(f"ActionToys Items found: {len(items)}")
        
        if len(items) == 0:
            print("Debugging HTML content (first 500 chars):")
            print(r.text[:500])
        else:
             print(f"First item: {items[0].get_text()[:50]}...")
    except Exception as e:
        print(f"ActionToys Failed: {e}")

if __name__ == "__main__":
    test_kidinn()
    test_actiontoys()
