import requests
from bs4 import BeautifulSoup

url = "https://fantasiapersonajes.es/?filter=brand%3AMATTEL&mot_p=2&mot_q=masters%20of%20the%20universe%20origins&sort=price%20asc"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
}

print(f"Fetching: {url}")
r = requests.get(url, headers=headers)
print(f"Status: {r.status_code}")
print(f"Length: {len(r.text)}")

soup = BeautifulSoup(r.text, 'html.parser')
items = soup.select('.product-miniature')
print(f"Found {len(items)} items with .product-miniature")

# Check for specific 'Motive' containers if standard ones aren't there
motive_items = soup.select('.motive-product') # Hypothesis
print(f"Found {len(motive_items)} items with .motive-product (hypothesis)")
