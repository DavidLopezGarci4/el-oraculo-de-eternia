import unittest
from models import ProductOffer

class TestProductOffer(unittest.TestCase):
    def test_normalization(self):
        """Test that title normalization removes unwanted keywords."""
        titulos = [
            ("Masters of the Universe Origins He-Man", "He-Man"),
            ("Figura Skeletor 14 cm MOTU", "Skeletor"),
            ("  Teela   Origins  Action Figure ", "Teela"),
            ("Masterverse Revelations Battle Cat", "Revelations Battle Cat")
        ]
        
        for raw, expected in titulos:
            with self.subTest(raw=raw):
                clean = ProductOffer._clean_title(raw)
                self.assertEqual(clean, expected)

    def test_display_price(self):
        """Test automatic display price formatting."""
        p = ProductOffer(
            name="Test",
            price_val=10.50,
            currency="€",
            url="http://test.com",
            image_url=None,
            store_name="TestStore"
        )
        self.assertEqual(p.display_price, "10.50€")

if __name__ == '__main__':
    unittest.main()
