
import requests

URL = "https://www.actionfigure411.com/masters-of-the-universe/origins-checklist.php"

def find_text():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    print(f"Fetching {URL}...")
    resp = requests.get(URL, headers=headers)
    text = resp.text
    print(f"Total Text Length: {len(text)}")
    
    markers = [
        "Origins Action Figures Checklist",
        "Origins Deluxe Checklist",
        "Beast Man (Cartoon Collection)",
        "Lord Gr'Asp"
    ]
    
    for m in markers:
        idx = text.find(m)
        print(f"MARKER '{m}': {idx}")

if __name__ == "__main__":
    find_text()
