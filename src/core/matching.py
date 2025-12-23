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
        self.series_tokens = {"origins", "masterverse", "cgi", "netflix", "filmation", "200x", "vintage", "commemorative"}

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

    def match(self, product_name: str, scraped_title: str, scraped_url: str) -> Tuple[bool, float, str]:
        """
        Returns (IsMatch, Score, Reason)
        """
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

        # --- Hard Check: Series Conflict ---
        # If DB says "Masterverse" and Scraped says "Origins" (or vice versa), it's a FAIL.
        # Note: We need to see if these tokens exist in the RAW text before normalization removed them?
        # Or ensure they are NOT in stop_words.
        # Current stop_words included "origins" & "masterverse". I need to remove them from proper stop_words list.
        # But wait, product names in DB might NOT have "Origins" in the name field if it's implicitly Category "Origins".
        # Assuming ProductModel.name contains the full name like "He-Man Origins".
        
        # We'll rely on the tokens we have.
        # (Self-Correction: I will update stop_words in __init__ to exclude crucial series names)
        
        # 3. Intersection Logic
        common = db_tokens.intersection(scraped_tokens)
        missing_from_db = db_tokens - common
        extra_in_scraped = scraped_tokens - db_tokens

        # Rule 1: Recall (Must match almost all DB tokens)
        # Allow 1 missing token ONLY if DB name has many tokens (>3).
        # "He-Man Battle Armor" (3) -> Missing "Armor" -> Fail.
        # "He-Man" (2) -> Missing "Man" -> Fail.
        
        # len(db_tokens) can be small (e.g. "Stratos").
        recall = len(common) / len(db_tokens)
        
        if recall < 1.0:
            # High strictness. If you don't match the DB name exactly, likely a Variant or different item.
            # Exception: "Webstor" vs "Webstor Figure".
            # If recall is high (e.g. > 0.8), maybe? 
            # Let's stick to 1.0 for checking DB tokens for now, unless DB has "Figure" which is a stopword.
            return False, recall, f"Missing DB tokens: {missing_from_db}"

        # Rule 2: Precision (Extra tokens in scraped)
        # If Scraped has "Battle Armor He-Man" and DB is "He-Man".
        # common={he, man}. extra={battle, armor}.
        # This is a VARIANT. We should NOT match it to the base figure.
        
        # Penalty for extra tokens
        # If extra tokens are numeric (year, size) they might be okay.
        # If extra tokens are words, they are likely variant descriptors.
        
        if len(extra_in_scraped) > 0:
            # Calculate overlap score (Jaccard-ish)
            # Jaccard = Common / Union
            union = db_tokens.union(scraped_tokens)
            jaccard = len(common) / len(union)
            
            # If jaccard is high (e.g. 0.8), it means extra tokens are few compared to total.
            # "He-Man Origins" (db) vs "He-Man Origins 2021" (scraped). J=3/4=0.75. Match? Yes.
            # "He-Man" (db) vs "He-Man Battle Armor" (scraped). J=2/4=0.5. Match? No.
            
            if jaccard >= 0.75:
                # Good match with some noise
                return True, jaccard, "High Jaccard Match"
            else:
                return False, jaccard, f"Too many extra tokens: {extra_in_scraped}"
        
        # Perfect Match (Recall 1.0, No Extra Tokens)
        return True, 1.0, "Perfect Match"
        """
        Converts text to improved set of significant tokens.
        1. Access URL slug if valid URL.
        2. Unidecode (remove accents).
        3. Lowercase.
        4. Split non-alphanumeric.
        5. Filter stop words.
        """
        if not text:
            return set()
            
        # URL Handling: extract slug
        if text.startswith("http"):
            try:
                path = urlparse(text).path
                text = path.replace("/", " ").replace("-", " ").replace("_", " ")
            except:
                pass
        
        # Standardize
        # Normalize unicode characters to ASCII (e.g. 'n' for 'ñ' if feasible, or just strip accents)
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
        text = text.lower()
        # Replace non-alphanumeric with space
        text = re.sub(r'[^a-z0-9]', ' ', text)
        
        tokens = set(text.split())
        significant_tokens = tokens - self.stop_words
        
        # Special filtering for single characters or numbers that might be noise?
        # Maybe keep numbers like '200x', 'v2'.
        return {t for t in significant_tokens if len(t) > 1 or t.isdigit()}

    def match(self, product_name: str, scraped_title: str, scraped_url: str) -> Tuple[bool, float, str]:
        """
        Returns (IsMatch, Score, Reason)
        """
        # 1. DB Tokens (The Truth)
        db_tokens = self.normalize(product_name)
        if not db_tokens:
            return False, 0.0, "Empty DB Name"

        # 2. Scraped Tokens (Title + URL)
        title_tokens = self.normalize(scraped_title)
        url_tokens = self.normalize(scraped_url)
        scraped_tokens = title_tokens | url_tokens
        
        if not scraped_tokens:
            return False, 0.0, "Empty Scraped Data"

        # 3. Intersection Logic
        common = db_tokens.intersection(scraped_tokens)
        missing_from_db = db_tokens - common
        extra_in_scraped = scraped_tokens - db_tokens

        # Rule 1: All DB tokens MUST be present in Scraped Data (Recall = 100%)
        # Exception: Sometimes 'He-Man' is just 'He Man'. Normalization handles that.
        # Exception: 'Buzz-Off' -> 'Buzz', 'Off'.
        if len(missing_from_db) > 0:
            # Allow 1 missing token if DB name is long? No, user wants precision.
            # Example: DB="Battle Armor He-Man", Scraped="He-Man". Missing="Battle", "Armor". -> Fail.
            return False, 0.0, f"Missing tokens: {missing_from_db}"

        # Rule 2: Extra tokens in Scraped Data checking (Precision)
        # If Scraped has "Battle Armor He-Man" and DB is "He-Man". common={"he", "man"}. extra={"battle", "armor"}.
        # This implies Scraped is a Variant, not the base product.
        # We need to penalize significant extra tokens.
        # But how do we know "Battle" is significant and not just a description like "Good Condition"?
        # We defined 'stop_words' to remove descriptions. 
        # So 'extra_in_scraped' contains potentially significant variant markers.
        
        # Logic: If I have > 0 extra significant tokens, score drops.
        # But maybe "Eternia" is extra? Or "Playset"?
        # Let's use Jaccard Index as the score.
        
        union = db_tokens.union(scraped_tokens)
        jaccard = len(common) / len(union)
        
        # Rule 3: Jaccard Threshold
        # "He-Man" (2) vs "He-Man Battle Armor" (4). Jaccard = 2/4 = 0.5.
        # "He-Man" (2) vs "He-Man Origins" (2 - Origins stripped). Jaccard = 1.0.
        
        # If Jaccard is 1.0, it's a Perfect Semantic Match (ignoring stopwords).
        # If Jaccard is low, it means there are many unmatched significant words.
        
        # Threshold: 0.6?
        # "Evil-Lyn" (2) vs "Evil-Lyn" (2). Jaccard=1.0.
        # "Evil-Lyn" (2) vs "Evil" (1). Missing "Lyn" -> Fail Rule 1.
        # "Evil" (1) vs "Evil-Lyn" (2). Common="Evil". Missing=None. Extra="Lyn". Jaccard=0.5.
        
        if jaccard >= 0.65:
            return True, jaccard, "High Jaccard"
        
        return False, jaccard, f"Low Jaccard (Extra: {extra_in_scraped})"
