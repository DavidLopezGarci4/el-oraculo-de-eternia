import httpx
import asyncio

async def test():
    urls = [
        "https://www.electropolis.es",
        "https://www.electropolis.es/zona-freaky/figuras/figuras.html",
        "https://www.electropolis.es/catalogsearch/result/?q=masters"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://www.google.com/"
    }

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        for url in urls:
            try:
                print(f"Testing {url}...")
                resp = await client.get(url, headers=headers)
                print(f"Status: {resp.status_code}")
                # print(resp.text[:200])
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
