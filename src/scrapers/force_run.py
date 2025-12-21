import asyncio
from src.scrapers.spiders.actiontoys import ActionToysSpider
from src.core.logger import setup_logging

async def main():
    setup_logging()
    spider = ActionToysSpider()
    print("Running ActionToysSpider directly...")
    items = await spider.search("auto")
    print(f"Found {len(items)} items.")
    for i in items[:3]:
        print(f"- {i.product_name} ({i.price} EUR)")

if __name__ == "__main__":
    asyncio.run(main())
