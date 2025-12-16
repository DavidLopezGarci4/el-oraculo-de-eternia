from dataclasses import dataclass
from typing import Optional
import re

@dataclass
class ProductOffer:
    """Standardized representation of a product offer from any store."""
    name: str
    price_val: float
    currency: str
    url: str
    image_url: Optional[str]
    store_name: str
    
    # Metadata for UI
    display_price: str = ""
    normalized_name: str = ""

    def __post_init__(self):
        if not self.display_price:
            self.display_price = f"{self.price_val:.2f}{self.currency}" if self.currency == "€" else f"{self.currency}{self.price_val:.2f}"
            
        if not self.normalized_name:
             self.normalized_name = self._clean_title(self.name)

    @staticmethod
    def _clean_title(titulo: str) -> str:
        """Centralized title normalization logic."""
        t = titulo.lower()
        t = re.sub(r'masters of the universe|motu|origins|masterverse|figura|action figure|\d+\s?cm', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t.title()
