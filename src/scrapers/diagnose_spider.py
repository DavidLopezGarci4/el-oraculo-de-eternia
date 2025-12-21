from playwright.async_api import async_playwright
import asyncio

async def debug():
    url = "https://actiontoys.es/figuras-de-accion/masters-of-the-universe/origins/"
    print(f"Browsing {url} with Playwright...")
    
    async with async_playwright() as p:
        # Launch headless=True first, if fails we might try headed
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        await page.goto(url, wait_until="domcontentloaded")
        print("Page loaded.")
        
        # Take screenshot
        screenshot_path = "c:\\Users\\dace8\\OneDrive\\Documentos\\Antigravity\\el_oraculo_de_eternia\\debug_actiontoys.png"
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        # Check selectors
        count_li = await page.locator("li.product").count()
        print(f"Found {count_li} 'li.product' elements.")
        
        if count_li > 0:
            first_html = await page.locator("li.product").first.inner_html()
            print("First Item Inner HTML:")
            print(first_html[:500])
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
