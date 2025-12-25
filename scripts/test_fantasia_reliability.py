import asyncio
import logging
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from src.infrastructure.scrapers.fantasia_scraper import FantasiaScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestFantasia")

async def test_reliability():
    scraper = FantasiaScraper()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Test URL (Known MOTU search)
        url = "https://fantasiapersonajes.es/busqueda?controller=search&s=masters+of+the+universe"
        logger.info(f"Navigating to {url}...")
        
        await scraper._safe_navigate(page, url)
        # Wait a bit for dynamic content if any
        await asyncio.sleep(2)
        
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Test JSON-LD
        json_results = scraper._extract_from_json_ld(soup)
        logger.info(f"JSON-LD Results: {len(json_results)} items.")
        
        # 2. Test CSS
        items = soup.select('article.product-miniature')
        logger.info(f"CSS Results: {len(items)} items.")
        
        if json_results:
            logger.info("VALIDATION: JSON-LD is WORKING on this page.")
            for i, p in enumerate(json_results[:3]):
                logger.info(f"  [JSON] {i+1}. {p.product_name} - {p.price} {p.currency}")
        else:
            logger.warning("VALIDATION: JSON-LD NOT FOUND on search page. CSS Fallback is mandatory.")
            
        if items:
            for i, item in enumerate(items[:3]):
                p = scraper._parse_html_item(item)
                if p:
                    logger.info(f"  [CSS] {i+1}. {p.product_name} - {p.price} {p.currency}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_reliability())
