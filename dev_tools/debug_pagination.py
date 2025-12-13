import requests
from bs4 import BeautifulSoup

# Testing if standard search handles "results per page" or "pagination"
# PrestaShop usually uses &resultsPerPage per page, or &p=2, or &page=2
base_url = "https://fantasiapersonajes.es/buscar"
params = {
    "controller": "search",
    "s": "masters of the universe origins",
    "resultsPerPage": 100, # common param
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
}

print(f"Fetching Standard with resultsPerPage=100")
r = requests.get(base_url, params=params, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')
items = soup.select('.product-miniature')
print(f"Found {len(items)} items using standard search & resultsPerPage=100")

# Try page 2
params2 = {
    "controller": "search",
    "s": "masters of the universe origins",
    "page": 2
}
print(f"Fetching Standard Page 2")
r2 = requests.get(base_url, params=params2, headers=headers)
soup2 = BeautifulSoup(r2.text, 'html.parser')
items2 = soup2.select('.product-miniature')
print(f"Found {len(items2)} items on Page 2")
