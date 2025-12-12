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

# --- CONFIGURACIÓN DE NAVEGADOR ESTÁTICO (HEADERS) ---
HEADERS_STATIC = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- FUNCIÓN 1: TRADEINN (Kidinn) - MODO ESTÁTICO ---
def buscar_kidinn():
    """Escanea la página de Masters del Universo de Kidinn (Modo Requests)."""
    url = "https://www.tradeinn.com/kidinn/es/masters-of-the-universe/5883/nm"
    productos = []
    print(f"🌍 Consultando Kidinn: {url}")
    
    try:
        r = requests.get(url, headers=HEADERS_STATIC, timeout=15)
        # Check simple anti-bot
        if r.status_code != 200:
            print(f"⚠️ Kidinn devolvió status {r.status_code}")
            return []
            
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Selectores (Mismos que antes, funcionan en estático)
        items = soup.select('div.js-product-list-item')
        
        for item in items:
            try:
                # Link
                link_obj = item.select_one('a.js-href_list_products')
                if not link_obj: continue
                link = link_obj['href']
                if not link.startswith('http'): 
                    link = "https://www.tradeinn.com" + link

                # Title
                titulo_obj = link_obj.select_one('h3 p') or link_obj.select_one('h3')
                titulo = titulo_obj.get_text(strip=True) if titulo_obj else "Desconocido"
                
                # Filtro
                if not any(x in titulo.lower() for x in ["origins", "motu", "masters", "he-man", "skeletor"]): continue
                
                # Price
                price_candidates = link_obj.select('div > p')
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
            except: continue
    except Exception as e:
        print(f"❌ Error Kidinn: {e}")
        
    return productos

# --- FUNCIÓN 2: ACTION TOYS - MODO ESTÁTICO ---
def buscar_actiontoys():
    """Escanea ActionToys (Modo Requests)."""
    base_url = "https://actiontoys.es/figuras-de-accion/masters-of-the-universe/"
    productos = []
    
    # En modo estático iteramos, pero requests es bloqueante, así que cuidado con muchas páginas.
    # Como corre en un hilo aparte, no bloquea la UI.
    url_actual = base_url
    pagina_num = 1
    max_paginas = 5
    
    while url_actual and pagina_num <= max_paginas:
        try:
            print(f"🌍 Consultando ActionToys p{pagina_num}: {url_actual}")
            r = requests.get(url_actual, headers=HEADERS_STATIC, timeout=15)
            if r.status_code != 200: break
            
            soup = BeautifulSoup(r.text, 'html.parser')
            
            items = soup.select('li.product, article.product-miniature, div.product-small')
            
            if not items:
                # Fallback
                links = soup.select('a.product-loop-title')
                if links: items = [l.parent for l in links]
                else: break 
            
            for item in items:
                try:
                    link_elem = item.select_one('a.product-loop-title')
                    if not link_elem: link_elem = item.select_one('a.woocommerce-LoopProduct-link') 
                    if not link_elem: continue
                    link = link_elem['href']
                    
                    titulo_obj = link_elem.select_one('h3') or item.select_one('h2.woocommerce-loop-product__title')
                    titulo = titulo_obj.get_text(strip=True) if titulo_obj else "Desconocido"
                    
                    if not any(x in titulo.lower() for x in ["origins", "motu", "masters", "he-man", "skeletor"]): continue

                    precio_obj = item.select_one('span.price')
                    precio = "Agotado"
                    precio_val = 9999.0
                    
                    if precio_obj:
                        precio = precio_obj.get_text(strip=True)
                        try:
                            clean_p = re.sub(r'[^\d,\.]', '', precio).replace(',','.')
                            precio_val = float(clean_p)
                        except: pass
                    
                    img_obj = item.select_one('img')
                    img_src = img_obj['src'] if img_obj else None
                    
                    productos.append({
                        "Figura": titulo,
                        "NombreNorm": limpiar_titulo(titulo),
                        "Precio": precio,
                        "PrecioVal": precio_val,
                        "Tienda": "ActionToys",
                        "Enlace": link,
                        "Imagen": img_src
                    })
                except: continue
            
            next_button = soup.select_one('a.next') or soup.select_one('a[rel="next"]')
            if next_button:
                url_actual = next_button['href']
                pagina_num += 1
            else:
                url_actual = None
        except Exception as e: 
            print(f"❌ Error ActionToys: {e}")
            break
            
    return productos

# --- ORQUESTADOR HÍBRIDO (ASYNC WRAPPER) ---
async def buscar_en_todas_async():
    """
    Ejecuta scrapers síncronos (requests) en hilos separados (asyncio.to_thread)
    para mantener el paralelismo y la velocidad.
    """
    # Lanzamos las dos funciones síncronas en paralelo usando hilos
    # Esto evita que una espere a la otra
    resultados = await asyncio.gather(
        asyncio.to_thread(buscar_kidinn),
        asyncio.to_thread(buscar_actiontoys)
    )
        
    # Aplanar resultados
    lista_final = [item for sublist in resultados for item in sublist]
    return lista_final

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
start = st.button("🚀 RASTREAR OFERTAS", type="primary")

if start:
    with st.spinner("⚡ Escaneando el multiverso (Paralelo)..."):
        # Llamada a la función con caché
        datos = obtener_datos_cacheados()
        
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
            st.warning("No se encontraron resultados. ¿Están caídas las webs?")
