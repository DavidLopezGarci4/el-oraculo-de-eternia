import asyncio
from src.scrapers.spiders.actiontoys import ActionToysSpider

async def test_actiontoys():
    spider = ActionToysSpider()
    # Test query that should return results
    results = await spider.search("Origins")
    
    print(f"\n--- Results ({len(results)}) ---")
    for r in results[:5]:
        print(f"[{r.shop_name}] {r.product_name} - {r.price}€")
        print(f"URL: {r.url}")
        print("---")

if __name__ == "__main__":
    asyncio.run(test_actiontoys())
