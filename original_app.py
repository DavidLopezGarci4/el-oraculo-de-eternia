import streamlit as st
import pandas as pd
import asyncio
# from playwright.async_api import async_playwright # REMOVED
from bs4 import BeautifulSoup
import os
# import subprocess # REMOVED
# import sys # REMOVED

# --- HACK DE DESPLIEGUE ELIMINADO ---
# Playwright ha sido removido para mejorar performance y estabilidad.


# Configuración de página con layout ancho para que quepa bien la tabla
st.set_page_config(page_title="Buscador MOTU Origins", layout="wide", page_icon="⚔️")

# --- HEADER & ESTILOS ---
st.markdown("""
    <style>
    .main-header {
        text-align: center; 
        font-family: 'Arial Black', sans-serif;
        color: #B22222;
        text-shadow: 2px 2px 0px #000;
        margin-bottom: 20px;
    }
    .sub-header {
        text-align: center;
        color: #555;
        font-style: italic;
        margin-bottom: 40px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>⚔️ Buscador MOTU Origins ⚔️</h1>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Rastreador de precios para coleccionistas - Masters of the Universe</div>", unsafe_allow_html=True)

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
    """
    Kidinn Scraper - DESACTIVADO TEMPORALMENTE (Fase H0).
    Razón: Inestabilidad y falta de API pública fiable.
    """
    log = ["⚠️ Kidinn desactivado por mantenimiento (Fase H0)."]
    return {'items': [], 'log': log}

# --- FUNCIÓN 2: ACTION TOYS (API MODE) ---
# --- FUNCIÓN 2: ACTION TOYS (API MODE VIA PLUGIN) ---
from scrapers.actiontoys import ActionToysScraper
from circuit_breaker import CircuitBreaker

from scrapers.fantasiapersonajes import FantasiaScraper
from scrapers.frikiverso import FrikiversoScraper

@st.cache_resource
def get_circuit_breaker():
    return CircuitBreaker(failure_threshold=3, recovery_timeout=60)

def buscar_actiontoys():
    """Wrapper para usar el nuevo ActionToysScraper con Circuit Breaker."""
    cb = get_circuit_breaker()
    scraper = ActionToysScraper()
    
    if not scraper.is_active:
        return {'items': [], 'log': ["⚠️ ActionToys desactivado."]}
        
    log = [f"⚡ Iniciando Plugin: {scraper.name}"]
    productos = []
    
    try:
        # Wrap search in Circuit Breaker
        offers = cb.call(scraper.search, "masters of the universe origins")
        log.append(f"✅ Plugin encontró {len(offers)} items.")
        
        # Mapping de Compatibilidad (Objeto -> Diccionario UI antigua)
        for p in offers:
            productos.append({
                "Figura": p.name,
                "NombreNorm": p.normalized_name,
                "Precio": p.display_price,
                "PrecioVal": p.price_val,
                "Tienda": p.store_name,
                "Enlace": p.url,
                "Imagen": p.image_url
            })
            
    except Exception as e:
        log.append(f"❌ Error Critical Plugin / Circuit Open: {e}")
        
    return {'items': productos, 'log': log}

def buscar_fantasia():
    """Wrapper para usar el nuevo FantasiaScraper con Circuit Breaker."""
    cb = get_circuit_breaker()
    scraper = FantasiaScraper()
    
    # Check if active logic could be added here if needed
    log = [f"⚡ Iniciando Plugin: {scraper.name}"]
    productos = []
    
    try:
        offers = cb.call(scraper.search, "masters of the universe origins")
        log.append(f"✅ Plugin encontró {len(offers)} items.")
        
        for p in offers:
            productos.append({
                "Figura": p.name,
                "NombreNorm": p.normalized_name,
                "Precio": p.display_price,
                "PrecioVal": p.price_val,
                "Tienda": p.store_name,
                "Enlace": p.url,
                "Imagen": p.image_url
            })
    except Exception as e:
        log.append(f"❌ Error Fantasia / Circuit Open: {e}")
        
    return {'items': productos, 'log': log}

def buscar_frikiverso():
    """Wrapper para Frikiverso."""
    cb = get_circuit_breaker()
    scraper = FrikiversoScraper()
    log = [f"⚡ Iniciando Plugin: {scraper.name}"]
    productos = []
    try:
        offers = cb.call(scraper.search, "masters of the universe origins")
        log.append(f"✅ Plugin encontró {len(offers)} items.")
        for p in offers:
            productos.append({
                "Figura": p.name,
                "NombreNorm": p.normalized_name,
                "Precio": p.display_price,
                "PrecioVal": p.price_val,
                "Tienda": p.store_name,
                "Enlace": p.url,
                "Imagen": p.image_url
            })
    except Exception as e:
        log.append(f"❌ Error Frikiverso: {e}")
    return {'items': productos, 'log': log}

# --- ORQUESTADOR HÍBRIDO (ASYNC WRAPPER) ---
async def buscar_en_todas_async():
    """
    Ejecuta scrapers síncronos (requests) en hilos separados (asyncio.to_thread)
    para mantener el paralelismo y la velocidad.
    Combina resultados y logs.
    """
    # Lanzamos las funciones síncronas en paralelo usando hilos
    # Esto evita que una espere a la otra
    resultados = await asyncio.gather(
        asyncio.to_thread(buscar_kidinn),
        asyncio.to_thread(buscar_actiontoys),
        asyncio.to_thread(buscar_fantasia),
        asyncio.to_thread(buscar_frikiverso)
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
# Estilos CSS Mejorados (CSS Grid + Mobile First)
st.markdown("""
<style>
    /* Contenedor Principal Grid */
    .product-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); /* 160px min width para móvil */
        gap: 12px;
        padding: 10px 0;
    }
    /* Tarjeta */
    .product-card {
        border: 1px solid #eee;
        border-radius: 10px;
        padding: 10px;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100%;
        transition: transform 0.1s ease;
    }
    .product-card:active {
        transform: scale(0.98);
    }
    /* Imagen */
    .product-img {
        width: 100%;
        height: 140px; /* Altura fija contenida */
        object-fit: contain;
        margin-bottom: 8px;
        background-color: #fff;
    }
    /* Título */
    .product-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 4px;
        line-height: 1.2;
        display: -webkit-box;
        -webkit-line-clamp: 2; /* Max 2 líneas */
        -webkit-box-orient: vertical;
        overflow: hidden;
        height: 2.4em; /* Forzar altura alineada */
    }
    /* Precio y Tienda */
    .price-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-top: auto;
        padding-top: 8px;
        border-top: 1px solid #f0f0f0;
    }
    .main-price {
        font-size: 1.1rem;
        font-weight: 800;
        color: #e63946;
    }
    .store-badge {
        font-size: 0.7rem;
        background: #f1f3f5;
        padding: 2px 6px;
        border-radius: 4px;
        color: #666;
    }
    /* Botón */
    .action-btn {
        display: block;
        width: 100%;
        text-align: center;
        background-color: #ff4b4b;
        color: white !important;
        text-decoration: none;
        padding: 8px 0;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.9rem;
        margin-top: 8px;
    }
    .action-btn:hover {
        opacity: 0.9;
    }
    
    /* MOBILE TWEAKS */
    @media (max-width: 480px) {
        .product-grid {
            grid-template-columns: repeat(2, 1fr); /* Forzar 2 columnas en móvil */
            gap: 8px;
        }
        .product-card {
            padding: 8px;
        }
        .product-img {
            height: 100px; /* Imagen más pequeña */
        }
        .product-title {
            font-size: 0.8rem; /* Texto más compacto */
            height: 2.8em; /* 3 líneas */
            -webkit-line-clamp: 3;
        }
        .main-price {
            font-size: 1rem;
        }
        .action-btn {
            font-size: 0.8rem;
            padding: 6px 0;
        }
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

    with st.spinner("⚡ Escaneando el multiverso..."):
        # Llamada a la función con caché
        datos, logs_debug = obtener_datos_cacheados()
        
        if datos:
            df = pd.DataFrame(datos)
            
            # --- LÓGICA DE AGRUPACIÓN ---
            grupos = df.groupby('NombreNorm')
            items_unicos = []
            
            for nombre, grupo in grupos:
                img_candidata = grupo['Imagen'].dropna().iloc[0] if not grupo['Imagen'].dropna().empty else "https://via.placeholder.com/150?text=No+Image"
                ofertas = grupo.sort_values('PrecioVal').to_dict('records')
                precio_min = ofertas[0]['Precio']
                
                # Link principal (la oferta más barata)
                link_principal = ofertas[0]['Enlace']
                tienda_principal = ofertas[0]['Tienda']
                
                items_unicos.append({
                    "Nombre": nombre,
                    "Imagen": img_candidata,
                    "PrecioDisplay": precio_min,
                    "PrecioVal": ofertas[0]['PrecioVal'],
                    "Tienda": tienda_principal,
                    "Link": link_principal,
                    "NumOfertas": len(ofertas)
                })
            
            # Ordenar por precio
            items_unicos.sort(key=lambda x: x['PrecioVal'])
            
            st.success(f"¡Combate finalizado! {len(items_unicos)} figuras únicas encontradas.")
            with st.expander("📝 Logs técnicos"):
                st.write(logs_debug)
                
            st.divider()

            # --- RENDERIZADO HTML GRID ---
            html_cards = ""
            for item in items_unicos:
                # Badge de "Más ofertas"
                more_offers = f"<span title='{item['NumOfertas']} ofertas disponibles'>+{item['NumOfertas']-1} más</span>" if item['NumOfertas'] > 1 else ""
                
                # IMPORTANT: No indentar el HTML dentro del string para evitar que Markdown lo interprete como código.
                card_html = f"""
<div class="product-card">
<img src="{item['Imagen']}" class="product-img" loading="lazy" alt="{item['Nombre']}">
<div class="product-title">{item['Nombre']}</div>
<div class="price-row">
<span class="main-price">{item['PrecioDisplay']}</span>
<span class="store-badge">{item['Tienda']} {more_offers}</span>
</div>
<a href="{item['Link']}" target="_blank" class="action-btn">VER OFERTA</a>
</div>
"""
                html_cards += card_html

            st.markdown(f'<div class="product-grid">{html_cards}</div>', unsafe_allow_html=True)
                            
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

