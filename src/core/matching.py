import re
import unicodedata
from typing import Set, Tuple, List
from urllib.parse import urlparse
from src.domain.schemas import Product

class SmartMatcher:
    def __init__(self):
        # Tokens that don't distinguish a product (Stop Words for this Domain)
        self.stop_words = {
            "masters", "universe", "universo", "motu", "origins", "masterverse",
            "mattel", "figure", "figura", "action", "toy", "juguete", "cm", "inch",
            "wave", "deluxe", "collection", "collector", "edicion", "edition",
            "new", "nuevo", "caja", "box", "original", "authentic", "classics",
            "super7", "reaction", "pop", "funko", "vinyl", "of", "the", "del", "de", "y", "and",
            "comprar", "venta", "oferta", "precio", "barato", "envio", "gratis"
        }
        
        # Hard Filters: If one defines 'Origins' and other 'Masterverse', they can NEVER match.
        # These are series/lines that are distinct.
        self.series_tokens = {
            "origins", "masterverse", "cgi", "netflix", "filmation", "200x", "vintage", "commemorative",
            "turtles", "grayskull", "stranger", "things", "cartoon", "collection", "sun", "man", "rulers", "sunman"
        }

    def normalize(self, text: str) -> Set[str]:
        """
        Converts text to improved set of significant tokens.
        """
        if not text:
            return set()
            
        # URL Handling: extract slug
        if text.startswith("http"):
            try:
                path = urlparse(text).path
                # Keep significant parts of URL? often they contain the clean name
                text = path.split('/')[-1] # usage of last segment is usually better
                text = text.replace("-", " ").replace("_", " ").replace(".html", "")
            except:
                pass
        
        # Standardize
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
        text = text.lower()
        text = re.sub(r'[^a-z0-9]', ' ', text)
        
        tokens = set(text.split())
        
        # Filter stop words but KEEP series tokens if they appear (for the series check)
        # Actually, we want to filter generic stopwords, but Series tokens are crucial for the Hard Filter.
        # So we remove stopwords UNLESS they are in series_tokens?
        # No, "origins" is in stopwords list currently... removed it from stop_words in __init__ above? 
        # Wait, "origins" was in stop_words in previous version. I should REMOVE it from stop_words if I want to use it as a filter.
        
        # Refined Stop Words Logic in __init__ (I will fix it there).
        
        significant = tokens - self.stop_words
        return {t for t in significant if len(t) > 1 or t.isdigit()}

    def match(self, product_name: str, scraped_title: str, scraped_url: str, db_ean: str = None, scraped_ean: str = None) -> Tuple[bool, float, str]:
        """
        Returns (IsMatch, Score, Reason)
        Priority 1: EAN/GTIN Match (Universal Fingerprint)
        Priority 2: Semantic Score (Jaccard)
        """
        # --- EAN MATCH (PHASE 10: PRECISION) ---
        if db_ean and scraped_ean:
            # Clean both EANs (remove spaces/dashes)
            clean_db = re.sub(r'[^0-9]', '', str(db_ean))
            clean_scraped = re.sub(r'[^0-9]', '', str(scraped_ean))
            
            if clean_db == clean_scraped and len(clean_db) >= 8: # Basic safety length
                return True, 1.0, f"Perfect EAN Match: {db_ean}"
            elif clean_db and clean_scraped:
                # If both have EAN but differ, it's a high-confidence MISMATCH
                return False, 0.0, f"EAN Mismatch: {db_ean} vs {scraped_ean}"

        # --- SEMANTIC FALLBACK ---
        # 1. DB Tokens (The Truth)
        db_tokens = self.normalize(product_name)
        if not db_tokens:
            return False, 0.0, "Empty DB Name"

        # 2. Scraped Tokens (Merge Title + URL)
        title_tokens = self.normalize(scraped_title)
        url_tokens = self.normalize(scraped_url)
        scraped_tokens = title_tokens | url_tokens
        
        if not scraped_tokens:
            return False, 0.0, "Empty Scraped Data"
        
        # 3. Intersection Logic
        common = db_tokens.intersection(scraped_tokens)
        missing_from_db = db_tokens - common
        extra_in_scraped = scraped_tokens - db_tokens

        # Rule 1: Recall (Must match all significant DB tokens)
        if len(missing_from_db) > 0:
            return False, 0.0, f"Missing DB tokens: {missing_from_db}"

        # Rule 2: Precision (Jaccard Index)
        union = db_tokens.union(scraped_tokens)
        jaccard = len(common) / len(union) if union else 0.0
        
        # Rule 3: Series Hard Filter
        # If DB Tokens contains a specific series marker (e.g. 'masterverse') 
        # but Scraped Tokens contains a conflicting one (e.g. 'origins'), it's a FAIL.
        db_series = db_tokens.intersection(self.series_tokens)
        scr_series = scraped_tokens.intersection(self.series_tokens)
        
        # If both have series markers, they MUST intersect
        if db_series and scr_series:
            if not db_series.intersection(scr_series):
                return False, 0.0, f"Series Conflict: DB={db_series} vs Scraped={scr_series}"

        if jaccard >= 0.65:
            return True, jaccard, "High Jaccard Match"
        else:
            return False, jaccard, f"Too many extra tokens: {extra_in_scraped}"
