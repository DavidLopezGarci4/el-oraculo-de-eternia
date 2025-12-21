import httpx
from bs4 import BeautifulSoup
import asyncio
import json

async def run():
    url = "https://dvdstorespain.es/es/257-merchandising-cine-series-y-videojuegos"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9"
    }
    
    titles = []
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Scrape first 10 pages (~200 items) to get coverage
        for page in range(1, 11):
            target = f"{url}?page={page}"
            print(f"Scraping {target}...")
            try:
                resp = await client.get(target, headers=headers)
                soup = BeautifulSoup(resp.text, 'html.parser')
                items = soup.select('.product-miniature')
                if not items: break
                
                for item in items:
                    t = item.select_one('.product-title a').get_text(strip=True)
                    titles.append(t)
            except Exception as e:
                print(e)
                
    with open("data/dump_dvd_titles.json", "w", encoding="utf-8") as f:
        json.dump(sorted(titles), f, indent=2, ensure_ascii=False)
    
    print(f"Dumped {len(titles)} titles.")

if __name__ == "__main__":
    asyncio.run(run())
