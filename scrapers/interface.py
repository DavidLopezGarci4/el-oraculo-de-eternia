from typing import List, Protocol, Dict, Any
from models import ProductOffer

class ScraperPlugin(Protocol):
    """Protocol that all store scrapers must implement."""
    
    def search(self, query: str) -> List[ProductOffer]:
        """
        Search for products based on a query string.
        Should return a clean list of ProductOffer or empty list on error.
        """
        ...
    
    @property
    def name(self) -> str:
        """Name of the store (e.g. 'ActionToys')."""
        ...
    
    @property
    def is_active(self) -> bool:
        """Feature flag to enable/disable scraper."""
        ...
