import requests

url = "https://fantasiapersonajes.es/?mot_q=masters%20of%20the%20universe%20origins&mot_s=388811"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
}

r = requests.get(url, headers=headers)
with open("fantasia.html", "w", encoding="utf-8") as f:
    f.write(r.text)

print(f"Downloaded {len(r.text)} bytes.")
