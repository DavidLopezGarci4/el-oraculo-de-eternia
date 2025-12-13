from bs4 import BeautifulSoup

with open("debug_item.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
item = soup # debug_item.html is the item fragment

print("--- DEBUGGING SELECTORS ---")

# Title
title_elem = item.select_one('.product-title a')
if title_elem:
    print(f"Title: {title_elem.get_text(strip=True)}")
else:
    print("Title: NOT FOUND")

# Link
if title_elem:
    print(f"Link: {title_elem.get('href')}")

# Price
price_elem = item.select_one('.product-price') or item.select_one('.product-price-and-shipping .price') or item.select_one('.price')
if price_elem:
    print(f"Price: {price_elem.get_text(strip=True)}")
else:
    print("Price: NOT FOUND")

# Image
img_elem = item.select_one('.thumbnail-container img')
if img_elem:
    src = img_elem.get('data-src') or img_elem.get('src')
    print(f"Image: {src}")
else:
    print("Image: NOT FOUND")
