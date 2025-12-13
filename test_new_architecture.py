from scrapers.actiontoys import ActionToysScraper
from models import ProductOffer

def test_scraper():
    print("Testing ActionToysScraper Class...")
    scraper = ActionToysScraper()
    print(f"Scraper: {scraper.name}, Active: {scraper.is_active}")
    
    results = scraper.search("masters of the universe origins")
    print(f"Results found: {len(results)}")
    
    if results:
        first = results[0]
        print(f"First item: {first.name} | {first.display_price}")
        assert isinstance(first, ProductOffer)
        assert first.store_name == "ActionToys"
    else:
        print("No results found!")
        
if __name__ == "__main__":
    test_scraper()
