import requests
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
}

def check_actiontoys_api():
    print("🔵 Probando ActionToys WP API...")
    # Endpoint moderno de WooCommerce Store API (suele ser público)
    url = "https://actiontoys.es/wp-json/wc/store/products?search=masters&per_page=10"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"✅ ÉXITO! Encontrados {len(data)} items via API.")
            if data:
                item = data[0]
                print(f"   Ejemplo: {item.get('name')} - {item.get('prices', {}).get('price', 'Sin precio')}")
            return True
        else:
            print("❌ API no disponible o bloqueada.")
    except Exception as e:
        print(f"❌ Error conectando: {e}")
    return False

def check_kidinn_search():
    print("\n🔵 Probando Kidinn Internal Search...")
    # Endpoint de búsqueda interna
    url = "https://www.tradeinn.com/index.php?action=search&search=masters+of+the+universe&products_per_page=10"
    # O la API oculta
    url_ajax = "https://www.tradeinn.com/kidinn/es/buscar/products-ajax?search=masters"
    
    try:
        r = requests.get(url_ajax, headers=HEADERS, timeout=10)
        print(f"Status Ajax: {r.status_code}")
        if r.status_code == 200:
             # A veces devuelve JSON, a veces HTML parcial
             try:
                 data = r.json()
                 print("✅ ÉXITO! JSON recibido de Kidinn.")
                 return True
             except:
                 print(f"⚠️ Recibido contenido no JSON ({len(r.text)} chars). Podría ser HTML usable.")
    except Exception as e:
        print(f"❌ Error conectando: {e}")
        
if __name__ == "__main__":
    check_actiontoys_api()
    check_kidinn_search()
