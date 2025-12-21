import aiohttp
import asyncio

async def test():
    urls = [
        "https://www.electropolis.es",
        "https://www.electropolis.es/zona-freaky/figuras/figuras.html"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }

    async with aiohttp.ClientSession() as session:
        for url in urls:
            try:
                print(f"Testing {url}...")
                async with session.get(url, headers=headers) as resp:
                    print(f"Status: {resp.status}")
                    text = await resp.text()
                    # print(text[:200])
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
