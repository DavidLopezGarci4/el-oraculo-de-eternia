import requests

# Standard PrestaShop search URL
url = "https://fantasiapersonajes.es/buscar?controller=search&s=masters+of+the+universe+origins"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
}

print(f"Testing URL: {url}")
r = requests.get(url, headers=headers)
print(f"Status: {r.status_code}")

if r.status_code == 200:
    print(f"Content Length: {len(r.text)}")
    if "product-miniature" in r.text or "product_list" in r.text:
        print("FOUND product-miniature/list!")
    
    # Save for inspection
    with open("fantasia_standard.html", "w", encoding="utf-8") as f:
        f.write(r.text)
