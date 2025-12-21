import asyncio
from src.scrapers.pipeline import ScrapingPipeline
from src.scrapers.spiders.fantasia import FantasiaSpider
# from src.scrapers.spiders.actiontoys import ActionToysSpider
from src.infrastructure.database import SessionLocal
from src.infrastructure.repositories.product import ProductRepository
from rapidfuzz import process, fuzz
from loguru import logger
import sys

# Configure logger to specifically show our analysis
logger.remove()
logger.add(sys.stderr, level="INFO")

async def analyze_matches():
    print("Analyzing Matching Logic...")
    
    # 1. Load DB Products
    db = SessionLocal()
    repo = ProductRepository(db)
    all_products = repo.get_all(limit=5000)
    product_map = {p.name: p for p in all_products}
    product_names = list(product_map.keys())
    db.close()
    
    print(f"Loaded {len(product_names)} products from DB.")
    
    # 2. Scrape Real Data
    print("Scraping Fantasia (auto)...")
    spider = FantasiaSpider()
    # Use "auto" to trigger the full keyword list
    results = await spider.search("auto") 
    
    print(f"Scraped {len(results)} items.")
    print("\n--- MATCH ANALYSIS (Normalized + Threshold 75) ---")
    print(f"{'SCORE':<5} | {'STATUS':<10} | {'CLEANED NAME':<50} | {'BEST DB MATCH'}")
    print("-" * 100)
    
    matches = 0
    misses = 0
    
    import re
    def clean_name(name):
        n = name.lower()
        # Specific fix for "Sun-Man" -> "Sun Man"
        n = n.replace("-", " ")
        
        remove_list = [
            "masters of the universe", "motu", "origins", 
            "figura", "figure", "action", "mattel", "14 cm", "14cm"
        ]
        for w in remove_list:
            n = n.replace(w, "")
        
        # Remove special chars but keep spaces
        n = re.sub(r'[^a-zA-Z0-9\s]', '', n)
        return " ".join(n.split())

    # Debug: Check specific internal DB names
    print(f"DB Check 'Sun-Man': {[p for p in product_names if 'sun' in p.lower() and 'man' in p.lower()]}")
    
    for offer in results:
        clean_scraped = clean_name(offer.product_name)
        
        # Use partial_token_set_ratio to handle "King Hiss" subset of "King Hiss (Deluxe)"
        match = process.extractOne(clean_scraped, product_names, scorer=fuzz.partial_token_set_ratio)
        
        if not match:
            continue
            
        best_name = match[0]
        score = match[1]
        
        # Threshold: Partial match is very generous, so we need a HIGH threshold (e.g. 90 or 100)
        # to avoid "Man" matching "He-Man".
        # Actually, "Man-At-Arms" vs "Man-E-Faces". "Man" is common.
        # Let's see the scores first.
        
        status = "MATCH" if score >= 85 else "MISS"
        if score >= 85:
            matches += 1
        else:
            misses += 1
            
        if score < 100: 
            print(f"{score:.1f} | {status} | {clean_scraped[:48]:<50} | {best_name}")

    print(f"\nSummary: Matches: {matches} | Misses: {misses}")
    print("Tip: If you see many 'MISS' with high scores (e.g. 70-84) that look correct, we should lower the threshold.")

if __name__ == "__main__":
    asyncio.run(analyze_matches())
