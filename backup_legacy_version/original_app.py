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
import re

# --- CONFIGURACIÓN DE NAVEGADOR ESTÁTICO (HEADERS STANDARD) ---
import json

HEADERS_STATIC = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/"
}

def limpiar_titulo(titulo):
    """Normaliza el título para agrupar productos similares."""
    import re
    # Eliminar palabras clave comunes para agrupar
    t = titulo.lower()
    t = re.sub(r'masters of the universe|motu|origins|masterverse|figura|action figure|\d+\s?cm', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t.title()

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
    """Escanea Kidinn usando búsqueda AJAX y estrategias robustas."""
    url = "https://www.tradeinn.com/kidinn/es/buscar/products-ajax"
    params = {
        "search": "masters of the universe origins", 
        "products_per_page": 48
    }
    
    log = [f"🌍 Conectando a Búsqueda Kidinn..."]
    productos = []
    
    try:
        r = requests.get(url, params=params, headers=HEADERS_STATIC, timeout=15)
        log.append(f"Status Code: {r.status_code}")
        
        # 1. INTENTO DE PARSEO JSON (A veces devuelve JSON con HTML dentro)
        html_content = r.text
        try:
            data = r.json()
            if isinstance(data, dict) and 'html' in data:
                html_content = data['html']
                log.append("✅ Detectado JSON con HTML incrustado. Extrayendo...")
        except:
            pass # No es JSON, seguimos como HTML plano
            
        log.append(f"🔍 Contenido a analizar: {len(html_content)} caracteres.")
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 2. DEBUG DE ENLACES (Chivato)
        all_links = soup.select('a')
        log.append(f"🔎 Total enlaces en página: {len(all_links)}")
        if all_links:
            ejemplos = [l.get('href', 'n/a') for l in all_links[:5]]
            log.append(f"🔎 Ejemplos de href: {ejemplos}")

        # 3. ESTRATEGIA JSON-LD (SEO)
        json_items = extraer_datos_json_ld(soup, "Kidinn")
        if json_items:
            log.append(f"✅ JSON-LD encontró {len(json_items)} items.")
            for p in json_items:
                if not p['Enlace'].startswith('http'):
                    p['Enlace'] = "https://www.tradeinn.com" + p['Enlace']
            return {'items': json_items, 'log': log}

        # 4. ESTRATEGIA VISUAL (IMAGEN -> LINK)
        # Si fallan las clases, buscamos imágenes de productos y subimos al enlace
        log.append("⚠️ Probando estrategia VISUAL (Imágenes)...")
        
        items = []
        # Buscamos imágenes que parezcan de productos (no iconos pequeños)
        candidate_imgs = soup.find_all('img')
        
        valid_containers = []
        seen_links = set()
        
        for img in candidate_imgs:
            # Subir hasta encontrar un <a>
            parent = img.find_parent('a')
            if not parent: continue
            
            href = parent.get('href', '')
            if not href or href in seen_links: continue
            
            # Filtros heurísticos
            # 1. Link debe ser relativo o tradeinn
            if href.startswith('http') and 'tradeinn.com' not in href: continue
             
            # 2. Debe parecer un producto (usualmente tiene ID numérico)
            if not re.search(r'\d+', href): continue
            
            # 3. La imagen no debe ser un pixel o icono (heuristicas de nombre)
            src = img.get('src', '')
            if 'icon' in src or 'logo' in src: continue
            
            valid_containers.append(parent)
            seen_links.add(href)
            
        if valid_containers:
            items = valid_containers[:48]
            log.append(f"✅ Estrategia VISUAL encontró {len(items)} candidatos.")
        else:
            log.append("❌ Estrategia VISUAL falló.")

        # PROCESAMIENTO
        items_procesados = 0
        for item in items:
            try:
                link = item['href']
                if not link.startswith('http'): link = "https://www.tradeinn.com" + link
                
                # Título: El texto del enlace o el alt de la imagen
                titulo = item.get_text(strip=True)
                if not titulo:
                    img = item.find('img')
                    if img: titulo = img.get('alt', '')
                    
                if not titulo: titulo = "Figura Sin Nombre"
                
                # DEBUG: Ver qué estamos descartando
                log.append(f"❓ Candidato procesado: '{titulo}' | Link: {link}")
                
                # Filtro de seguridad (DESACTIVADO TEMPORALMENTE PARA DEBUG)
                # if "motu" not in titulo.lower() and "masters" not in titulo.lower() and "origins" not in titulo.lower():
                #      log.append(f"🗑️ Filtered: {titulo}")
                #      continue

                # Precio
                # A veces el precio no está dentro del <a>, sino al lado.
                # Intentamos buscar en el padre del <a> (el div contenedor)
                container = item.parent
                full_text = container.get_text(separator=' ', strip=True) if container else ""
                
                # Regex Precio
                price_match = re.search(r'(\d+[\.,]\d{2})\s?[€$]', full_text)
                precio = "Ver Web"
                precio_val = 9999.0
                
                if price_match:
                    precio = price_match.group(0)
                    try:
                        precio_val = float(price_match.group(1).replace(',','.'))
                    except: pass
                
                # Imagen
                img_obj = item.find('img')
                img_src = img_obj.get('src') if img_obj else None
                
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
                 log.append(f"⚠️ Error item visual: {item_e}")
                 continue
                 
        log.append(f"Kidinn: {items_procesados} items procesados.")
        return {'items': productos, 'log': log}
        
    except Exception as e:
        log.append(f"❌ Error Kidinn: {e}")
        return {'items': [], 'log': log}

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

