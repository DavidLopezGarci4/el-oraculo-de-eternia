import asyncio
import httpx
from bs4 import BeautifulSoup

async def test_pixelatoy():
    # Magic URL from legacy
    url = "https://www.pixelatoy.com/es/module/ambjolisearch/jolisearch"
    params = {
        "s": "masters ", 
        "ajs_cat": "309",
        "order": "product.price.asc",
        "resultsPerPage": "9999999"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"Testing {url} with params {params}...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, params=params, headers=headers)
            print(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                items = soup.select('.product-miniature')
                if not items:
                     items = soup.select('.ajax_block_product')
                     
                print(f"Items found via HTML: {len(items)}")
            else:
                print("Error:", resp.text[:200])
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_pixelatoy())
