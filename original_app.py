import streamlit as st
import pandas as pd
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import os
import subprocess
import sys

# --- HACK DE DESPLIEGUE: INSTALAR NAVEGADORES ---
# Streamlit Cloud no tiene los navegadores instalados por defecto.
try:
    # Usamos subprocess para que espere a que termine la instalación antes de seguir
    # Instalamos TODO (incluyendo headless-shell que es lo que fallaba)
    print("🔧 Instalando navegadores Playwright...")
    subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
    print("✅ Navegadores instalados correctamente.")
except Exception as e:
    print(f"⚠️ Error instalando navegadores: {e}")


# Configuración de página con layout ancho para que quepa bien la tabla
st.set_page_config(page_title="Rastreador Master MOTU", page_icon="⚔️", layout="wide")

# --- UTILIDADES DE NORMALIZACIÓN (NUEVO) ---
import requests

# --- CONFIGURACIÓN DE NAVEGADOR ESTÁTICO (HEADERS STANDARD) ---
import json

HEADERS_STATIC = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/"
}

# --- HELPER: JSON-LD EXTRACTOR ---
def extraer_datos_json_ld(soup, source_tag):
    """Intenta extraer productos de metadatos JSON-LD (SEO)."""
    productos = []
    scripts = soup.find_all('script', type='application/ld+json')
    
    for script in scripts:
        try:
            data = json.loads(script.string)
            # Normalizar a lista si es dict único
            if isinstance(data, dict):
                data = [data]
            
            for entry in data:
                # Caso 1: ItemList (Catálogos)
                if entry.get('@type') == 'ItemList' and 'itemListElement' in entry:
                    for item in entry['itemListElement']:
                        # A veces el producto está directo, a veces en 'item'
                        prod = item.get('item', item)
                        if not isinstance(prod, dict): continue
                        
                        titulo = prod.get('name', 'Desconocido')
                        link = prod.get('url', 'No Link')
                        if link == 'No Link' and 'url' in item: link = item['url'] # Fallback
                        
                        image = prod.get('image', None)
                        if isinstance(image, list): image = image[0]
                        elif isinstance(image, dict): image = image.get('url')
                        
                        price = 0.0
                        price_str = "Ver Web"
                        
                        offers = prod.get('offers')
                        if isinstance(offers, dict):
                            price = float(offers.get('price', 0))
                            price_str = f"{price}€"
                        elif isinstance(offers, list) and offers:
                            price = float(offers[0].get('price', 0))
                            price_str = f"{price}€"
                            
                        # Filtro básico
                        if "motu" not in titulo.lower() and "masters" not in titulo.lower(): continue
                        
                        productos.append({
                            "Figura": titulo,
                            "NombreNorm": limpiar_titulo(titulo),
                            "Precio": price_str,
                            "PrecioVal": price,
                            "Tienda": source_tag,
                            "Enlace": link,
                            "Imagen": image
                        })

                # Caso 2: Product Single (Ficha de producto - raro en listados pero posible)
                if entry.get('@type') == 'Product':
                    titulo = entry.get('name', 'Desconocido')
                    # ... (Lógica similar, simplificada por brevedad) ...
                    # En listados suele ser ItemList.
        except: continue
        
    return productos

# --- FUNCIÓN 1: TRADEINN (Kidinn) ---
def buscar_kidinn():
    """Escanea Kidinn y devuelve dict con items y logs."""
    url = "https://www.tradeinn.com/kidinn/es/masters-of-the-universe/5883/nm"
    log = [f"🌍 Conectando a Kidinn: {url}"]
    productos = []
    
    try:
        r = requests.get(url, headers=HEADERS_STATIC, timeout=15)
        log.append(f"Status Code: {r.status_code}")
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # ESTRATEGIA 1: JSON-LD (SEO DATA)
        json_items = extraer_datos_json_ld(soup, "Kidinn")
        if json_items:
            log.append(f"✅ JSON-LD encontró {len(json_items)} items. Usando datos estructurados.")
            # Ajuste de enlaces relativos si los hay
            for p in json_items:
                if not p['Enlace'].startswith('http'):
                    p['Enlace'] = "https://www.tradeinn.com" + p['Enlace']
            return {'items': json_items, 'log': log}
            
        log.append("⚠️ JSON-LD no encontró nada. Probando selectores HTML...")
        
        # ESTRATEGIA 2: HTML SCRAPING (FALLBACK)
        items = soup.select('div.js-product-list-item')
        if not items:
            # Fallback selectors (Broad)
            items = soup.select('div.product-grid-item, div.search-product-item, div.item, div.item_container, div[data-id]')
            log.append(f"⚠️ Selector principal falló. Fallbacks encontraron: {len(items)}")
            
            # Último intento: Buscar enlaces directos si no hay cajas
            if not items:
                 potential_links = soup.select('a[href*="/masters-of-the-universe/"]')
                 if potential_links:
                     items = [p.parent for p in potential_links[:36]] # Limitamos a parent directo
                     log.append(f"⚠️ Fallback enlaces directos encontró: {len(items)}")

        log.append(f"Items a procesar: {len(items)}")
        
        items_procesados = 0
        for idx, item in enumerate(items):
            # DEBUG SUPREMO: Ver el HTML del primer item
            if idx == 0:
                log.append(f"📦 DEBUG HTML KIDINN ITEM 0: {str(item)[:600]}")
                
            try:
                # Link
                link_obj = item.select_one('a.js-href_list_products, a')
                if not link_obj: 
                    log.append(f"⚠️ Item {idx} sin link (Kidinn)")
                    continue
                link = link_obj['href']
                if not link.startswith('http'): link = "https://www.tradeinn.com" + link

                # Title
                titulo_obj = link_obj.select_one('h3 p') or link_obj.select_one('h3') or item.select_one('p.name')
                titulo = titulo_obj.get_text(strip=True) if titulo_obj else "Desconocido"
                
                # Filtro
                if not any(x in titulo.lower() for x in ["origins", "motu", "masters", "he-man", "skeletor"]): 
                    # log.append(f"🗑️ Filtered: {titulo}") # Demasiado ruido si son muchos
                    continue
                
                # Price
                price_candidates = link_obj.select('div > p, span.price')
                precio = "Agotado"
                precio_val = 9999.0
                
                for p in price_candidates:
                    text = p.get_text(strip=True)
                    if any(c in text for c in ['€', '$']):
                        precio = text
                        try:
                            precio_val = float(text.replace('€','').replace('$','').replace(',','.').strip())
                        except: pass
                        break
                
                # Imagen
                img_obj = item.select_one('img')
                img_src = img_obj['src'] if img_obj else None
                
                productos.append({
                    "Figura": titulo,
                    "NombreNorm": limpiar_titulo(titulo),
                    "Precio": precio,
                    "PrecioVal": precio_val,
                    "Tienda": "Kidinn",
                    "Enlace": link,
                    "Imagen": img_src
                })
                items_procesados += 1
            except Exception as item_e:
                log.append(f"⚠️ Error procesando item Kidinn: {item_e}")
                continue
        log.append(f"Kidinn: {items_procesados} items válidos extraídos.")
    except Exception as e:
        log.append(f"❌ Excepción crítica en Kidinn: {str(e)}")
        
    return {'items': productos, 'log': log}

# --- FUNCIÓN 2: ACTION TOYS (API MODE) ---
def buscar_actiontoys():
    """Escanea ActionToys usando su API pública (WooCommerce)."""
    # Endpoint directo, sin parsear HTML. Mucho más rápido y sin bloqueos.
    url_api = "https://actiontoys.es/wp-json/wc/store/products"
    params = {
        "search": "masters of the universe origins",
        "per_page": 50, # Pedimos 50 de una vez
        "page": 1
    }
    
    log = [f"🌍 Consultando API ActionToys: {url_api}"]
    productos = []
    
    while True:
        try:
            r = requests.get(url_api, params=params, headers=HEADERS_STATIC, timeout=15)
            log.append(f"API Página {params['page']} Status: {r.status_code}")
            
            if r.status_code != 200: break
            
            data = r.json()
            if not data: break # Fin de resultados
            
            log.append(f"API encontró {len(data)} items.")
            
            for item in data:
                try:
                    titulo = item.get('name', 'Desconocido')
                    # Filtro de seguridad
                    if "masters" not in titulo.lower() and "origins" not in titulo.lower(): continue
                    
                    price_data = item.get('prices', {})
                    # El precio viene en céntimos (ej: 2249 -> 22.49) o string formateado
                    price_val = float(price_data.get('price', 0)) / 100.0
                    price_str = f"{price_val:.2f}€"
                    
                    link = item.get('permalink')
                    
                    # Imagen
                    images = item.get('images', [])
                    img_src = images[0].get('src') if images else None
                    
                    productos.append({
                        "Figura": titulo,
                        "NombreNorm": limpiar_titulo(titulo),
                        "Precio": price_str,
                        "PrecioVal": price_val,
                        "Tienda": "ActionToys",
                        "Enlace": link,
                        "Imagen": img_src
                    })
                except: continue
            
            # Paginación
            if len(data) < params['per_page']: break # Si devuelve menos de los pedidos, es la última
            params['page'] += 1
            if params['page'] > 5: break # Límite de seguridad
            
        except Exception as e:
            log.append(f"❌ Error API ActionToys: {e}")
            break
            
    return {'items': productos, 'log': log}

# (Resto de código antiguo borrado/comentado para evitar conflictos)


# --- ORQUESTADOR HÍBRIDO (ASYNC WRAPPER) ---
async def buscar_en_todas_async():
    """
    Ejecuta scrapers síncronos (requests) en hilos separados (asyncio.to_thread)
    para mantener el paralelismo y la velocidad.
    Combina resultados y logs.
    """
    # Lanzamos las dos funciones síncronas en paralelo usando hilos
    # Esto evita que una espere a la otra
    resultados = await asyncio.gather(
        asyncio.to_thread(buscar_kidinn),
        asyncio.to_thread(buscar_actiontoys)
    )
        
    # Aplanar resultados y agregar logs
    lista_productos = []
    lista_logs = []
    
    for res in resultados:
        lista_productos.extend(res['items'])
        lista_logs.extend(res['log'])
        
    return lista_productos, lista_logs

# --- CACHÉ Y WRAPPER ---
# TTL = 3600 segundos (1 hora). show_spinner=False para controlar mensaje propio
@st.cache_data(ttl=3600, show_spinner=False)
def obtener_datos_cacheados():
    """Llamada síncrona cacheada."""
    return asyncio.run(buscar_en_todas_async())

# --- INTERFAZ ---
st.title("⚔️ Buscador Unificado MOTU Origins")

# Estilos CSS Mejorados
st.markdown("""
<style>
    .stButton button { width: 100%; border-radius: 8px; font-weight: 600; }
    .card-container {
        border: 1px solid #ddd;
        border-radius: 12px;
        padding: 12px;
        background: white;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        height: 100%; /* Igualar alturas */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .price-tag {
        font-size: 1.1rem;
        font-weight: bold;
        color: #2e7bcf;
    }
    .store-row {
        display: flex;
        justify_content: space-between;
        align-items: center;
        margin-top: 5px;
        padding-top: 5px;
        border-top: 1px solid #eee;
    }
</style>
""", unsafe_allow_html=True)

# Botón Principal
col_btn1, col_btn2 = st.columns([3, 1])
if col_btn1.button("🚀 RASTREAR OFERTAS", type="primary"):
    start = True
else:
    start = False

if col_btn2.button("🧹 LIMPIAR CACHÉ"):
    st.cache_data.clear()
    st.toast("Memoria borrada. La próxima búsqueda será fresca.", icon="🧹")

if start:

    with st.spinner("⚡ Escaneando el multiverso (Paralelo)..."):
        # Llamada a la función con caché
        datos, logs_debug = obtener_datos_cacheados()
        
        if datos:
            df = pd.DataFrame(datos)
            
            # --- LÓGICA DE AGRUPACIÓN ---
            # Agrupamos por 'NombreNorm'
            grupos = df.groupby('NombreNorm')
            
            items_unicos = []
            
            for nombre, grupo in grupos:
                # Seleccionamos la mejor imagen (la primera que no sea None, o la primera del grupo)
                img_candidata = grupo['Imagen'].dropna().iloc[0] if not grupo['Imagen'].dropna().empty else None
                
                # Ordenamos las ofertas de este muñeco por precio
                ofertas = grupo.sort_values('PrecioVal').to_dict('records')
                
                # Precio mínimo para mostrar "Desde X"
                precio_min = ofertas[0]['Precio']
                
                items_unicos.append({
                    "Nombre": nombre, # Título limpio
                    "Imagen": img_candidata,
                    "PrecioMin": ofertas[0]['PrecioVal'],
                    "PrecioDisplay": precio_min,
                    "Ofertas": ofertas # Lista de diccionarios {Tienda, Precio, Enlace...}
                })
            
            # Ordenar los grupos por el precio más bajo que tengan
            items_unicos.sort(key=lambda x: x['PrecioMin'])
            
            st.success(f"¡Combate finalizado! {len(items_unicos)} figuras únicas encontradas (de {len(df)} ofertas).")
            with st.expander("📝 Logs técnicos (Click para ver)"):
                st.write(logs_debug)
                
            st.divider()

            # --- RENDERIZADO DE TARJETAS ---
            cols = st.columns(2)
            
            for idx, item in enumerate(items_unicos):
                with cols[idx % 2]:
                    with st.container(border=True):
                        # Imagen
                        if item['Imagen']:
                            st.image(item['Imagen'], use_container_width=True)
                        else:
                            st.markdown("🖼️ *Sin Imagen*")
                        
                        # Título
                        st.markdown(f"#### {item['Nombre']}")
                        
                        # Lista de Ofertas (Comparador)
                        st.caption("Ofertas disponibles:")
                        
                        for oferta in item['Ofertas']:
                            # Diseño compacto por oferta: "Kidinn: 15€ [Link]"
                            c1, c2 = st.columns([2, 1])
                            c1.markdown(f"**{oferta['Tienda']}**: {oferta['Precio']}")
                            c2.link_button("Ir", oferta['Enlace'], help=f"Comprar en {oferta['Tienda']}")
                            
        else:
            st.error("❌ No se encontraron resultados.")
            
            # MOSTRAR LOGS EN PANTALLA PRINCIPAL SI FALLA
            st.warning("Parece que Skeletor ha bloqueado la conexión. Aquí tienes el informe técnico:")
            with st.container(border=True):
                st.markdown("### 🕵️‍♂️ Informe de Debugging")
                for linea in logs_debug:
                    if "❌" in linea or "⚠️" in linea:
                        st.error(linea)
                    else:
                        st.text(linea)

