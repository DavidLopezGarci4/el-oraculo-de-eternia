import asyncio
import time
from typing import List
from playwright.async_api import async_playwright, BrowserContext
from src.infrastructure.scrapers.base import BaseScraper
from src.scrapers.base import ScrapedOffer

class MockScraper(BaseScraper):
    async def run(self, context: BrowserContext) -> List[ScrapedOffer]:
        page = await context.new_page()
        urls = [
            "https://www.google.com",
            "https://www.bing.com",
            "https://www.wikipedia.org"
        ]
        
        intervals = []
        last_time = time.time()
        
        for url in urls:
            print(f"--- Attempting navigation to {url} ---")
            await self._safe_navigate(page, url)
            current_time = time.time()
            elapsed = current_time - last_time
            intervals.append(elapsed)
            print(f"Elapsed since last nav attempt: {elapsed:.2f}s")
            last_time = current_time
            
        await page.close()
        return intervals

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        scraper = MockScraper("TestJitter", "https://example.com")
        intervals = await scraper.run(context)
        
        print("\n--- Summary ---")
        for i, interval in enumerate(intervals):
            print(f"Navigation {i+1}: {interval:.2f}s delay detected.")
            if 2.0 <= interval <= 7.0: # 5s jitter + small overhead
                print("[PASS]")
            else:
                print("[FAIL] (Outside expected range)")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
