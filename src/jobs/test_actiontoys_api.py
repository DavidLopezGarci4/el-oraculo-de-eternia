import asyncio
import httpx
import json
import traceback

async def test_api():
    url = "https://actiontoys.es/wp-json/wc/store/products"
    params = {
        "search": "Masters of the Universe",
        "per_page": 5
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"Testing {url}...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, params=params, headers=headers)
            print(f"Status: {resp.status_code}")
            print(f"Preview: {resp.text[:200]}")
        except Exception:
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api())
