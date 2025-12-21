import httpx
from bs4 import BeautifulSoup
import asyncio

async def test():
    # Attempt Faceted Search URL for "Marca Mattel"
    # PrestaShop often uses "Marca" or "Brand". Given previous "brand:Mattel" attempt, let's try standard PS Faceted Search format.
    # q=Marca-Mattel is standard.
    urls = [
        "https://dvdstorespain.es/es/257-merchandising-cine-series-y-videojuegos?q=Marca-Mattel",
        "https://dvdstorespain.es/es/257-merchandising-cine-series-y-videojuegos?q=Fabricante-Mattel"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9"
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for url in urls:
            print(f"Testing Facet URL: {url}")
            try:
                resp = await client.get(url, headers=headers)
                print(f"Status: {resp.status_code}")
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                total_elem = soup.select_one('.total-products')
                if total_elem:
                    print(f"Total Count Text: {total_elem.get_text(strip=True)}")
                else:
                    items = soup.select('.product-miniature')
                    print(f"Items on page 1: {len(items)}")

            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
