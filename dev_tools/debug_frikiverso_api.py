import requests

def test_frikiverso_internal_api():
    # Many PrestaShop modules proxy the API
    url = "https://frikiverso.es/module/motive/front"
    # Also try the standard search controller with motive params
    url2 = "https://frikiverso.es/buscar"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    params = {
        "action": "search",
        "mot_q": "masters of the universe",
        "q": "masters of the universe"
    }
    
    print("Testing /module/motive/front...")
    try:
        r = requests.post(url, data=params, headers=headers, timeout=5)
        print(f"POST Status: {r.status_code}")
        print(f"Content: {r.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_frikiverso_internal_api()
