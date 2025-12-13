import requests

endpoint = "https://fantasiapersonajes.es/module/motive/front"
engine_id = "596a63a0-96cb-40d9-8d1e-ac6c35623b09"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json"
}

# Try standard search payload
payload = {
    "xEngineId": engine_id,
    "query": "masters of the universe origins",
    "page": 1,
    "limit": 20
}

print(f"Testing Motive API: {endpoint}")
try:
    # Try POST
    r = requests.post(endpoint, json=payload, headers=headers)
    print(f"POST Status: {r.status_code}")
    if r.status_code == 200:
        print("Response (first 500 chars):")
        print(r.text[:500])
    
    # Try GET
    params = {
        "xEngineId": engine_id,
        "q": "masters of the universe origins"
    }
    r = requests.get(endpoint, params=params, headers=headers)
    print(f"GET Status: {r.status_code}")
    if r.status_code == 200:
        print("Response (first 500 chars):")
        print(r.text[:500])

except Exception as e:
    print(f"Error: {e}")
