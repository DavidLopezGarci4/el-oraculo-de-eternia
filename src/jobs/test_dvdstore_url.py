import httpx
from bs4 import BeautifulSoup
import asyncio

async def test():
    url = "https://dvdstorespain.es/es/?filter=f245%3AMERCHANDISING&filter=brand%3AMattel&mot_p=1&mot_q=masters%20of%20the%20universe"
    # Note: User had mot_p=2, I'll start with 1 to see the start.
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9"
    }
    
    print(f"Testing URL: {url}")
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers=headers)
            print(f"Status: {resp.status_code}")
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.product-miniature')
            print(f"Items found on page: {len(items)}")
            
            for item in items[:5]:
                title = item.select_one('.product-title a').get_text(strip=True)
                print(f" - {title}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
