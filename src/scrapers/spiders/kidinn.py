from typing import List
from playwright.async_api import async_playwright
from src.scrapers.base import BaseSpider, ScrapedOffer
from loguru import logger
import random
import asyncio

class KidInnSpider(BaseSpider):
    def __init__(self):
        super().__init__(shop_name="KidInn")
        self.base_url = "https://www.tradeinn.com/kidinn/es"

    async def search(self, query: str) -> List[ScrapedOffer]:
        async with async_playwright() as p:
            # Launch browser in headless mode (or not for debugging)
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Anti-detect measures: Random wait
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            search_url = f"{self.base_url}/busqueda?products_search[query]={query}"
            logger.info(f"KidInn: Navigating to {search_url}")
            
            try:
                await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                
                # Check for cookie consent
                # await page.click('#onetrust-accept-btn-handler', timeout=3000) # Example selector
                
                # Wait for results - GENERIC selector fallback
                await page.wait_for_selector('div.product_box', timeout=20000)
                
                items = await page.query_selector_all('div.product_box')
                
                offers = []
                for item in items[:5]: # Top 5 results
                    try:
                        title_el = await item.query_selector('.product_title')
                        price_el = await item.query_selector('.total_price')
                        link_el = await item.query_selector('a')
                        
                        if title_el and price_el:
                            title = await title_el.inner_text()
                            price_text = await price_el.inner_text()
                            # Clean price (e.g., "€ 15.99")
                            price = float(price_text.replace('€', '').replace(',', '.').strip())
                            
                            link = await link_el.get_attribute('href')
                            full_link = f"https://www.tradeinn.com{link}"
                            
                            offers.append(ScrapedOffer(
                                product_name=title.strip(),
                                price=price,
                                url=full_link,
                                shop_name=self.shop_name
                            ))
                    except Exception as e:
                        logger.warning(f"KidInn: Error parsing item: {e}")
                        continue
                        
                return offers
                
            except Exception as e:
                logger.error(f"KidInn Spider Failed: {e}")
                return []
            finally:
                await browser.close()
