import requests
from bs4 import BeautifulSoup

def get_titles(page):
    url = "https://fantasiapersonajes.es/buscar"
    params = {
        "controller": "search",
        "s": "masters of the universe origins",
        "page": page
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
    }
    r = requests.get(url, params=params, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    items = soup.select('.product-miniature .product-title a')
    titles = [t.get_text(strip=True) for t in items]
    return titles

print("Fetching Page 1...")
p1 = get_titles(1)
print(f"Page 1: {len(p1)} items")
print(p1[:3])

print("\nFetching Page 2...")
p2 = get_titles(2)
print(f"Page 2: {len(p2)} items")
print(p2[:3])

intersection = set(p1).intersection(set(p2))
print(f"\nOverlap: {len(intersection)}")
if len(intersection) == 0 and len(p2) > 0:
    print("SUCCESS: Pages contain distinct items.")
else:
    print("WARNING: Pages might be identical or empty.")
