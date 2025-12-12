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
import re

def limpiar_titulo(titulo):
    """Normaliza el nombre de la figura para la agrupación."""
    # Convertir a minúsculas
    texto = titulo.lower()
    
    # Lista de palabras "ruido" a eliminar para encontrar el nombre clave
    palabras_ruido = [
        r"masters of the universe", r"masters del universo", r"maestros del universo",
        r"origins", r"motu", r"mattel", r"figura", r"figure", r"action", r"acción",
        r"de", r"la", r"el", r"the", r"collection", r"colección", r"vintage",
        r"masterverse", r"new", r"nuevo", r"\d+cm", r"\d+ cm", r"-", r"–", r"\."
    ]
    
    for patron in palabras_ruido:
        texto = re.sub(patron, "", texto)
        
    # Limpieza final
    texto = " ".join(texto.split()) # Quitar espacios extra
    return texto.title() # Devolver en formato Título

# --- FUNCIÓN 1: TRADEINN (Kidinn) ---
async def buscar_kidinn(page):
    """Escanea la página de Masters del Universo de Kidinn."""
    # url = "https://www.tradeinn.com/kidinn/es/masters-of-the-universe/5883/nm" 
    # Url cambiada a veces, usamos la base si falla, pero mantenemos la lógica actual
    url = "https://www.tradeinn.com/kidinn/es/masters-of-the-universe/5883/nm"
    productos = []
    try:
        # Navegar
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        # Scroll rápido
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1500) # Reducido un poco
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        items = soup.select('div.js-product-list-item')
        
        for item in items:
            try:
                link_obj = item.select_one('a.js-href_list_products')
                if not link_obj: continue
                link = link_obj['href']
                if not link.startswith('http'): 
                    link = "https://www.tradeinn.com" + link

                titulo_obj = link_obj.select_one('h3 p') or link_obj.select_one('h3')
                titulo = titulo_obj.get_text(strip=True) if titulo_obj else "Desconocido"
                
                if not any(x in titulo.lower() for x in ["origins", "motu", "masters", "he-man", "skeletor"]): continue
                
                price_candidates = link_obj.select('div > p')
                precio = "Agotado" # Valor por defecto seguro
                precio_val = 9999.0 # Para ordenar
                
                for p in price_candidates:
                    text = p.get_text(strip=True)
                    if any(c in text for c in ['€', '$']):
                        precio = text
                        # Intentar extraer valor numérico para ordenar
                        try:
                            precio_val = float(text.replace('€','').replace('$','').replace(',','.').strip())
                        except: pass
                        break
                
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
        print(f"Error Kidinn: {e}") # Usamos print para no ensuciar UI si es background
        
    return productos

# --- FUNCIÓN 2: ACTION TOYS ---
async def buscar_actiontoys(page):
    """Escanea ActionToys."""
    url_actual = "https://actiontoys.es/figuras-de-accion/masters-of-the-universe/"
    productos = []
    pagina_num = 1
    max_paginas = 5
    
    while url_actual and pagina_num <= max_paginas:
        try:
            await page.goto(url_actual, wait_until="domcontentloaded", timeout=30000)
            await page.evaluate("window.scrollTo(0, 500)")
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            items = soup.select('li.product, article.product-miniature, div.product-small')
            
            if not items:
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
                            # Limpieza básica de precio '25,90 €' -> 25.90
                            clean_p = re.sub(r'[^\d,\.]', '', precio).replace(',','.')
                            precio_val = float(clean_p)
                        except: pass
                    
                    img_obj = item.select_one('img')
                    img_src = img_obj['src'] if img_obj else None
                    
                    productos.append({
                        "Figura": titulo,
                        "NombreNorm": limpiar_titulo(titulo),
                        "Precio": precio,
                        "PrecioVal": precio_val, # Útil para ordenar ofertas
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
        except: break
            
    return productos

# --- ORQUESTADOR PARALELO ---
async def buscar_en_todas_async():
    """Ejecuta los scrapers en paralelo para mejorar velocidad."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Contexto compartido optimizado
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        
        # Abrimos 2 páginas en paralelo (pestañas)
        page1 = await context.new_page()
        page2 = await context.new_page()
        
        # Lanzamos las tareas a la vez
        # asyncio.gather espera a que TODAS terminen
        # Devolvemos una tupla con los resultados
        resultados = await asyncio.gather(
            buscar_kidinn(page1),
            buscar_actiontoys(page2)
        )
        
        await browser.close()
        
        # Aplanar la lista de listas [[kidinn], [action]] -> [todos]
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
