import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import sys

# --- FUNCIÓN 1: TRADEINN (Kidinn) ---
async def buscar_kidinn(page):
    """Escanea la página de Masters del Universo de Kidinn."""
    print("--- Searching Kidinn ---")
    url = "https://www.tradeinn.com/kidinn/es/masters-of-the-universe/5883/nm"
    productos = []
    try:
        # Navegar y esperar la carga del DOM
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Scroll para cargar lazy-load
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Selectores Updated based on inspection
        # Container seems to be div.js-product-list-item
        items = soup.select('div.js-product-list-item')
        print(f"Kidinn: Found {len(items)} items in DOM")
        
        # DEBUG IMAGE
        if items:
            item = items[0]
            print("DEBUG: analyzing first Kidinn item for images...")
            imgs = item.select('img')
            for i, img in enumerate(imgs):
                print(f"  Img {i}: class={img.get('class')} src={img.get('src')}")

        for item in items:
            try:
                # Link
                link_obj = item.select_one('a.js-href_list_products')
                if not link_obj: continue
                link = link_obj['href']
                if not link.startswith('http'): 
                    link = "https://www.tradeinn.com" + link

                # Title: Now seems to be h3 > p inside the link
                titulo_obj = link_obj.select_one('h3 p') or link_obj.select_one('h3')
                titulo = titulo_obj.get_text(strip=True) if titulo_obj else "Nombre no detectado"
                
                # Filter
                if not any(x in titulo.lower() for x in ["origins", "motu", "masters", "he-man", "skeletor"]): 
                    continue
                
                # Price
                price_candidates = link_obj.select('div > p')
                precio = "Sin precio"
                for p in price_candidates:
                    text = p.get_text(strip=True)
                    if '€' in text or '$' in text or text.replace(',','').replace('.','').isdigit():
                        precio = text
                        break
                
                productos.append({
                    "Figura": titulo,
                    "Precio": precio,
                    "Tienda": "Kidinn",
                    "Enlace": link
                })
            except Exception as e: 
                # print(f"Error parsing item: {e}")
                continue
    except Exception as e:
        print(f"Error escaneando Kidinn: {e}")
        
    return productos

# --- FUNCIÓN 2: ACTION TOYS (Con Paginación) ---
async def buscar_actiontoys(page):
    """Escanea todas las páginas de la sección MOTU de ActionToys."""
    print("--- Searching ActionToys ---")
    url_actual = "https://actiontoys.es/figuras-de-accion/masters-of-the-universe/"
    productos = []
    pagina_num = 1
    max_paginas = 1 # Just 1 page for debug
    
    while url_actual and pagina_num <= max_paginas:
        try:
            print(f"ActionToys Page {pagina_num}: {url_actual}")
            await page.goto(url_actual, wait_until="domcontentloaded", timeout=30000)
            
            # Scroll a bit to ensure elements render
            await page.evaluate("window.scrollTo(0, 500)")
            await page.wait_for_timeout(1000)

            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Selectores Updated: It seems to be WooCommerce structure or similar
            items = soup.select('li.product, article.product-miniature, div.product-small')
            
            if not items: 
                # Fallback: look for the title link directly to identify containers
                print("Standard containers not found, trying link-based discovery...")
                links = soup.select('a.product-loop-title')
                if links:
                    items = [l.parent for l in links] # Assuming parent is container-ish
                else:
                    print("No items found on this page.")
                    break 
            
            print(f"Found {len(items)} items on page {pagina_num}")

            # DEBUG IMAGE
            if items:
                item = items[0]
                print("DEBUG: analyzing first Action item for images...")
                imgs = item.select('img')
                for i, img in enumerate(imgs):
                    print(f"  Img {i}: class={img.get('class')} src={img.get('src')}")

            for item in items:
                try:
                    # Link & Title
                    link_elem = item.select_one('a.product-loop-title')
                    if not link_elem:
                        # Try finding any link with title inside
                        link_elem = item.select_one('a.woocommerce-LoopProduct-link') 
                    
                    if not link_elem: continue
                    
                    link = link_elem['href']
                    
                    # Title inside the link (h3) or class
                    titulo_obj = link_elem.select_one('h3') or item.select_one('h2.woocommerce-loop-product__title')
                    titulo = titulo_obj.get_text(strip=True) if titulo_obj else "Sin nombre"
                    
                    if not any(x in titulo.lower() for x in ["origins", "motu", "masters", "he-man", "skeletor"]): continue

                    # Price
                    precio_obj = item.select_one('span.price')
                    precio = precio_obj.get_text(strip=True) if precio_obj else "Sin precio"
                    
                    productos.append({
                        "Figura": titulo,
                        "Precio": precio,
                        "Tienda": "ActionToys",
                        "Enlace": link
                    })
                except Exception as e:
                    # print(f"Error parsing Action item: {e}")
                    continue
            
            # Pagination
            next_button = soup.select_one('a.next') or soup.select_one('a[rel="next"]')
            if next_button:
                url_actual = next_button['href']
                pagina_num += 1
            else:
                url_actual = None
                
        except Exception as e:
            print(f"Error en ActionToys p{pagina_num}: {e}")
            break
            
    return productos

# --- ORQUESTADOR: Inicializa Playwright y coordina las búsquedas ---
async def debug_run():
    """Ejecuta todas las funciones de scraping de forma coordinada."""
    lista_maestra = []
    
    print("Launching browser...")
    # Usamos Playwright para simular el navegador
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Navegador invisible
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 1. KIDINN
        res_kidinn = await buscar_kidinn(page)
        print(f"Kidinn Results: {len(res_kidinn)}")
        if res_kidinn: print(res_kidinn[0])

        
        # 2. ACTION TOYS
        res_action = await buscar_actiontoys(page)
        print(f"ActionToys Results: {len(res_action)}")
        if res_action: print(res_action[0])
        
        await browser.close()
        
    return lista_maestra

if __name__ == "__main__":
    asyncio.run(debug_run())
