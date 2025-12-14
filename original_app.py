import streamlit as st
import pandas as pd
import asyncio
import aiohttp
import os
import json
from logger import log_structured
from models import ProductOffer
from scrape_run_report import ScrapeRunReporter, PageAudit # Integration


# Import Plugins
from scrapers.actiontoys import ActionToysScraper
from scrapers.fantasiapersonajes import FantasiaScraper
from scrapers.frikiverso import FrikiversoScraper
from scrapers.pixelatoy import PixelatoyScraper
from scrapers.electropolis import ElectropolisScraper
# from scrapers.dvdstorespain import DVDStoreSpainScraper


# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Buscador MOTU Origins", layout="wide", page_icon="⚔️")

# --- ESTILOS CSS GRID ---
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
    .product-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 12px;
        padding: 10px 0;
    }
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
    .product-img {
        width: 100%;
        height: 140px;
        object-fit: contain;
        margin-bottom: 8px;
        background-color: #fff;
    }
    .product-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 4px;
        line-height: 1.2;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        height: 2.4em;
    }
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
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>⚔️ Buscador MOTU Origins ⚔️</h1>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Rastreador de precios para coleccionistas - Masters of the Universe</div>", unsafe_allow_html=True)

# --- QUERY & CACHE LOGIC ---

# --- QUERY & CACHE LOGIC ---

async def run_scrapers_parallel(query: str, progress_callback=None):
    """
    Orchestrates the async scraping using aiohttp.
    """
    results = []
    logs = []
    
    # Plugins list
    plugins = [
        ActionToysScraper,
        FantasiaScraper,
        FrikiversoScraper,
        PixelatoyScraper,
        ElectropolisScraper,
        # DVDStoreSpainScraper
    ]
    total_plugins = len(plugins)
    
    # Initialize Reporter
    reporter = ScrapeRunReporter(
        category_name=query,
        parallel_between_stores=True,
        parallel_within_store=True,
        environment="streamlit_async"
    )
    
    async with aiohttp.ClientSession() as session:
        # Instantiate plugins
        active_scrapers = []
        store_runs = {}
        tasks = []
        
        for PluginCls in plugins:
            scraper = PluginCls(session=session)
            active_scrapers.append(scraper)
            
            # Register store debug info
            sr = reporter.store_start(scraper.name, "ASYNC_HTML_API", scraper.base_url)
            store_runs[scraper.name] = sr
            
        # Prepare tasks with name wrapping to keep track of who finished
        tasks = []
        for scraper in active_scrapers:
            # We wrap the coroutine to return the scraper name too
            async def wrapped_search(s=scraper):
                return s, await s.search(query)
            
            tasks.append(asyncio.create_task(wrapped_search()))
            logs.append(f"⚡ Iniciando: {scraper.name}")
            
        # Execute Concurrently with Progress Updates
        completed_count = 0
        
        for finished_task in asyncio.as_completed(tasks):
            try:
                # Unpack the result from our wrapper
                scraper_obj, outcome = await finished_task
                completed_count += 1
                
                if progress_callback:
                    progress_callback(completed_count / total_plugins)

                if isinstance(outcome, list):
                    results.extend(outcome)
                    logs.append(f"✅ {scraper_obj.name}: {len(outcome)} items encontrados.")
                elif isinstance(outcome, Exception):
                     logs.append(f"❌ {scraper_obj.name} Error: {str(outcome)}")
                     
            except Exception as e:
                logs.append(f"❌ CRITICAL TASK ERROR: {e}")
        
    # Finalize Report
    report_path = reporter.finalize()
    logs.append(f"📄 Informe generado: {report_path}")
                
    return results, logs

def render_sword_progress(percent: float):
    """Renders a custom HTML progress bar with a Sword indicator."""
    pct_int = int(percent * 100)
    
    # Helper to prevent sword from overflowing right edge
    sword_pos = f"calc({pct_int}% - 20px)" if pct_int > 5 else f"{pct_int}%"
    
    bar_html = f"""
    <div style="width: 100%; background-color: #e0e0e0; border-radius: 10px; height: 24px; position: relative; margin-top: 10px; margin-bottom: 24px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.2);">
        <div style="width: {pct_int}%; background-color: #B22222; height: 100%; border-radius: 10px; transition: width 0.5s ease; box-shadow: 0 0 10px rgba(178, 34, 34, 0.5);"></div>
        <div style="position: absolute; width: 100%; text-align: center; top: 2px; font-size: 14px; color: white; font-weight: 800; text-shadow: 1px 1px 2px black; z-index: 5;">{pct_int}%</div>
        <div style="position: absolute; left: {sword_pos}; top: -20px; font-size: 32px; transition: left 0.5s ease; z-index: 10; filter: drop-shadow(2px 2px 2px rgba(0,0,0,0.5));">⚔️</div>
    </div>
    """
    st.markdown(bar_html, unsafe_allow_html=True)

# Main Execution Wrapper
async def execute_search(query):
    progress_placeholder = st.empty()
    
    def update_bar(p):
        with progress_placeholder.container():
             render_sword_progress(p)
             
    # Initial render
    update_bar(0.0)
    
    products, logs = await run_scrapers_parallel(query, progress_callback=update_bar)
    
    # Final render 100%
    update_bar(1.0)
    await asyncio.sleep(0.5) 
    progress_placeholder.empty() # Clear bar after done
    
    return products, logs

# --- UI CONTROLS ---

col1, col2 = st.columns([3, 1])
start_btn = col1.button("🚀 RASTREAR OFERTAS", type="primary")
if col2.button("🧹 LIMPIAR CACHÉ"):
    st.cache_data.clear()
    st.toast("Caché limpiada.", icon="🧹")

# --- MAIN EXECUTION ---
if start_btn:
    # No st.spinner here because we use the custom sword bar!
    # st.markdown("### ⚔️ Escaneando los confines de Eternia...")
    
    # Run Async without cache for now to demonstrate bar (or adapt cache to store results only)
    # Caching the *Progress Bar* is impossible.
    # So we use cache_data on the RESULT, but the progress bar only shows on MISS.
    # To show bar every time, we might skip cache or manage it differently.
    # User asked for bar -> implies they want to see it load.
    
    all_products, debug_logs = asyncio.run(execute_search("masters of the universe"))
    
    # ... Processing DataFrame code (unchanged) ...
    if all_products:
        
        if all_products:
            # Convert to DataFrame for Grouping
            data_dicts = []
            for p in all_products:
                data_dicts.append({
                    "Nombre": p.name,
                    "PrecioVal": p.price_val,
                    "PrecioDisplay": p.display_price,
                    "Tienda": p.store_name,
                    "Enlace": p.url,
                    "Imagen": p.image_url,
                    "NombreNorm": p.normalized_name
                })
                
            df = pd.DataFrame(data_dicts)
            
            # --- GROUPING LOGIC ---
            # Group by Normalized Name to show "X ofertas"
            grouped_items = []
            for norm_name, group in df.groupby("NombreNorm"):
                # Sort group by price
                sorted_group = group.sort_values("PrecioVal")
                best_offer = sorted_group.iloc[0]
                
                # Image Strategy: First valid image in group
                valid_imgs = group['Imagen'].dropna()
                img = valid_imgs.iloc[0] if not valid_imgs.empty else "https://via.placeholder.com/150"
                
                grouped_items.append({
                    "Nombre": best_offer["Nombre"], # Use title of best offer
                    "Imagen": img,
                    "PrecioDisplay": best_offer["PrecioDisplay"],
                    "PrecioVal": best_offer["PrecioVal"],
                    "Tienda": best_offer["Tienda"],
                    "Link": best_offer["Enlace"],
                    "NumOfertas": len(group)
                })
            
            # Final Sort by Price
            grouped_items.sort(key=lambda x: x['PrecioVal'])
            
            # Render Grid
            st.success(f"¡Combate finalizado! {len(grouped_items)} figuras únicas encontradas.")
            
            html_cards = ""
            for item in grouped_items:
                 more_offers = f"<span title='{item['NumOfertas']} ofertas disponibles'>+{item['NumOfertas']-1} más</span>" if item['NumOfertas'] > 1 else ""
                 
                 # Minified HTML to prevent Markdown parser issues
                 card_html = f"""<div class="product-card"><img src="{item['Imagen']}" class="product-img" loading="lazy" alt="{item['Nombre']}"><div class="product-title">{item['Nombre']}</div><div class="price-row"><span class="main-price">{item['PrecioDisplay']}</span><span class="store-badge">{item['Tienda']} {more_offers}</span></div><a href="{item['Link']}" target="_blank" class="action-btn">VER OFERTA</a></div>"""
                 html_cards += card_html
                 
            st.markdown(f'<div class="product-grid">{html_cards}</div>', unsafe_allow_html=True)
            
            with st.expander("📝 Logs Técnicos (Async Build)"):
                st.write(debug_logs)
                
        else:
            st.error("No se encontraron productos.")
            st.write(debug_logs)
