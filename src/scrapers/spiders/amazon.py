from typing import List
from playwright.async_api import async_playwright
from src.scrapers.base import BaseSpider, ScrapedOffer
from loguru import logger
import random
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

class AmazonSpider(BaseSpider):
    def __init__(self):
        super().__init__(shop_name="Amazon")
        self.base_url = "https://www.amazon.es"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def search(self, query: str) -> List[ScrapedOffer]:
        async with async_playwright() as p:
            # Amazon often detects headless. 
            # We can use a real user agent and potentially run in HEADED mode if configured (hardcoded headless=True for now)
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            page = await context.new_page()
            
            # Anti-detect measures
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            search_url = f"{self.base_url}/s?k={query}"
            logger.info(f"Amazon: Navigating to {search_url}")
            
            try:
                await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                
                # Verify we are not blocked (CAPTCHA check)
                if await page.query_selector("input#captchacharacters"):
                    logger.warning("Amazon: CAPTCHA detected!")
                    raise Exception("Amazon CAPTCHA detected")

                # Wait for results
                await page.wait_for_selector('div[data-component-type="s-search-result"]', timeout=20000)
                
                items = await page.query_selector_all('div[data-component-type="s-search-result"]')
                
                # Fallback if specific component not found
                if not items:
                     items = await page.query_selector_all('.s-result-item')

                offers = []
                for item in items[:5]: # Top 5 results
                    try:
                        # Try multiple title selectors
                        title_el = await item.query_selector('h2 a span')
                        if not title_el:
                             title_el = await item.query_selector('span.a-text-normal')

                        # Try multiple price selectors
                        price_whole_el = await item.query_selector('.a-price-whole')
                        
                        link_el = await item.query_selector('h2 a')
                        if not link_el:
                            link_el = await item.query_selector('.a-link-normal')
                        
                        if title_el and price_whole_el and link_el:
                            title = await title_el.inner_text()
                            
                            price_whole = await price_whole_el.inner_text()
                            # Handle fractions if present, default to 00
                            price_fraction = await price_fraction_el.inner_text() if price_fraction_el else "00"
                            
                            price_text = f"{price_whole.replace('.', '')}.{price_fraction}"
                            price = float(price_text.replace(',', '.'))
                            
                            link = await link_el.get_attribute('href')
                            full_link = f"{self.base_url}{link}"
                            
                            offers.append(ScrapedOffer(
                                product_name=title.strip(),
                                price=price,
                                url=full_link,
                                shop_name=self.shop_name
                            ))
                    except Exception as e:
                        # logger.debug(f"Amazon: Skipping item due to: {e}")
                        continue
                        
                return offers
                
            except Exception as e:
                logger.error(f"Amazon Spider Failed: {e}")
                # Re-raise for Tenacity to retry
                raise e
            finally:
                await browser.close()
