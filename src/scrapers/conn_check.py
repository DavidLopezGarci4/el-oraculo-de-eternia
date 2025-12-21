import requests
from loguru import logger

def check_site(url, name):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        logger.info(f"{name}: Status {resp.status_code}")
        if resp.status_code == 200:
            logger.info(f"{name}: Content length {len(resp.text)}")
            if "captcha" in resp.text.lower():
                logger.warning(f"{name}: CAPTCHA detected in text")
            
            if name == "Amazon":
                with open("amazon_debug.html", "w", encoding="utf-8") as f:
                    f.write(resp.text)
        else:
            logger.warning(f"{name}: Blocked/Error")
    except Exception as e:
        logger.error(f"{name}: Failed - {e}")

if __name__ == "__main__":
    check_site("https://www.tradeinn.com/kidinn/es/busqueda?products_search[query]=He-Man", "KidInn")
    check_site("https://www.amazon.es/s?k=He-Man", "Amazon")
