from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        url = "https://www.electropolis.es"
        print(f"Navigating to {url}...")
        response = page.goto(url)
        print(f"Status: {response.status}")
        print(f"Title: {page.title()}")
        browser.close()

if __name__ == "__main__":
    run()
