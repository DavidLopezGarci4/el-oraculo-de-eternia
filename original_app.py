import streamlit as st
import pandas as pd
import asyncio
import aiohttp
import os
import base64
from logger import log_structured
from models import ProductOffer
from scrape_run_report import ScrapeRunReporter, PageAudit

# Import Plugins
from scrapers.actiontoys import ActionToysScraper
from scrapers.fantasiapersonajes import FantasiaScraper
from scrapers.frikiverso import FrikiversoScraper
from scrapers.pixelatoy import PixelatoyScraper
from scrapers.electropolis import ElectropolisScraper
# from scrapers.dvdstorespain import DVDStoreSpainScraper

# --- HELPER FUNCTIONS ---
def load_image_as_base64(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Buscador Coleccionista", layout="wide", page_icon="⚔️")

# --- ESTILOS CSS GRID & MOBILE OPTIMIZATIONS ---
st.markdown("""
    <style>
    /* Mobile-First Grid */
    .product-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); 
        gap: 10px;
        padding: 10px 0;
    }
    .product-card {
        border: 1px solid #f0f0f0;
        border-radius: 8px;
        padding: 8px;
        background: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100%;
        transition: transform 0.1s ease;
    }
    
    /* Make buttons touch-friendly */
    div.stButton > button {
        width: 100%;
        min-height: 44px;
    }
    
    /* Hide specific Streamlit elements if needed */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .product-img {
        width: 100%;
        height: 140px;
        object-fit: contain;
        margin-bottom: 8px;
        background-color: white;
        padding: 5px;
    }
    .product-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #222;
        margin-bottom: 4px;
        line-height: 1.25;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        height: 2.5em;
    }
    .price-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-top: auto;
        padding-top: 8px;
        border-top: 1px solid #eee;
    }
    .main-price {
        font-size: 1rem;
        font-weight: 800;
        color: #d32f2f;
    }
    .store-badge {
        font-size: 0.65rem;
        background: #f5f5f5;
        padding: 2px 5px;
        border-radius: 4px;
        color: #666;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 80px;
    }
    .action-btn {
        display: block;
        width: 100%;
        text-align: center;
        background-color: #d32f2f;
        color: white !important;
        text-decoration: none;
        padding: 6px 0;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        margin-top: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER IMAGE ---
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    try:
        st.image("Masters_buscador.png", use_container_width=True)
    except Exception:
        st.markdown("<h2 style='text-align: center; color: #d32f2f;'>⚔️ MOTU FINDER ⚔️</h2>", unsafe_allow_html=True)

# --- QUERY & CACHE LOGIC ---

async def run_scrapers_parallel(query: str, progress_callback=None):
    results = []
    logs = []
    
    plugins = [
        ActionToysScraper,
        FantasiaScraper,
        FrikiversoScraper,
        PixelatoyScraper,
        ElectropolisScraper,
    ]
    total_plugins = len(plugins)
    
    reporter = ScrapeRunReporter(
        category_name=query,
        parallel_between_stores=True,
        parallel_within_store=True,
        environment="streamlit_async"
    )
    
    async with aiohttp.ClientSession() as session:
        active_scrapers = []
        tasks = []
        
        for PluginCls in plugins:
            scraper = PluginCls(session=session)
            active_scrapers.append(scraper)
            reporter.store_start(scraper.name, "ASYNC_HTML_API", scraper.base_url)
            
        tasks = []
        for scraper in active_scrapers:
            async def wrapped_search(s=scraper):
                return s, await s.search(query)
            
            tasks.append(asyncio.create_task(wrapped_search()))
            
        completed_count = 0
        
        for finished_task in asyncio.as_completed(tasks):
            try:
                scraper_obj, outcome = await finished_task
                completed_count += 1
                
                if progress_callback:
                    progress_callback(completed_count / total_plugins)

                if isinstance(outcome, list):
                    results.extend(outcome)
                    logs.append(f"✅ {scraper_obj.name}: {len(outcome)} items found.")
                elif isinstance(outcome, Exception):
                     logs.append(f"❌ {scraper_obj.name} Error: {str(outcome)}")
                     
            except Exception as e:
                logs.append(f"❌ CRITICAL ERROR: {e}")
        
    report_path = reporter.finalize()
    logs.append(f"📄 Report: {report_path}")
                
    return results, logs

def render_sword_progress(percent: float):
    """
    Sword Progress Bar V8 - "Power of Grayskull" Edition.
    Features massive exterior glow and fluid internal gradient.
    """
    pct_int = int(percent * 100)
    
    # IDs
    mask_id = f"mask_{pct_int}"
    grad_id = f"grad_{pct_int}"
    blur_filter_id = f"blur_{pct_int}"
    
    # PATH DEFINITION
    # Reusing the exact same path data for all layers to ensure alignment
    sword_path = "M10,30 L40,18 L250,18 C260,18 260,8 280,8 L295,8 C305,8 305,24 315,24 L360,24 C370,24 370,36 360,36 L315,36 C305,36 305,52 295,52 L280,52 C260,52 260,42 250,42 L40,42 Z"
    
    svg_code = f"""
    <svg width="100%" height="80" viewBox="0 -10 400 80" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <!-- 1. FLUID ENERGY GRADIENT (Core) -->
            <linearGradient id="{grad_id}" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#FFFFFF" />    <!-- White Source -->
                <stop offset="30%" stop-color="#00FFFF" />   <!-- Cyan Plasma -->
                <stop offset="100%" stop-color="#0088FF" />  <!-- Electric Blue -->
            </linearGradient>
            
            <!-- 2. BLUR FILTER (For Exterior Glow) -->
            <filter id="{blur_filter_id}" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
            </filter>
            
            <!-- 3. PROGRESS MASK -->
            <mask id="{mask_id}">
                <!-- White reveals. We use a rect that grows with % -->
                <rect x="0" y="-10" width="{pct_int}%" height="100" fill="white" />
            </mask>
        </defs>
        
        <g stroke="none">
             <!-- LAYER 1: BASE (The Empty Sword Container) -->
             <path d="{sword_path}" fill="#222" stroke="#444" stroke-width="1" />
             
             <!-- LAYER 2: THE ENERGY (Masked by Progress) -->
             <g mask="url(#{mask_id})">
                 <!-- A. OUTSIDE GLOW (Behind) -->
                 <!-- We draw the same sword, filled with bright CYAN, and heavily blurred -->
                 <path d="{sword_path}" fill="#00FFFF" filter="url(#{blur_filter_id})" opacity="0.8" />
                 
                 <!-- B. FLUID CORE (Front) -->
                 <!-- We draw the sword again, filled with the gradient -->
                 <path d="{sword_path}" fill="url(#{grad_id})" />
             </g>
             
             <!-- LAYER 3: HARDWARE DETAILS (Overlay) -->
             <!-- Handle/Guard details that should sit ON TOP of the glow logic -->
             <path d="M40,30 L250,30" stroke="#003366" stroke-width="1" stroke-opacity="0.3" />
             <path d="M265,24 L300,24" stroke="#003366" stroke-width="1" stroke-opacity="0.5" />
             <path d="M265,36 L300,36" stroke="#003366" stroke-width="1" stroke-opacity="0.5" />
        </g>
        
        <text x="200" y="65" font-family="Arial, sans-serif" font-size="11" fill="#777" text-anchor="middle">
             {pct_int}%
        </text>
    </svg>
    """
    
    svg_code_oneline = " ".join(svg_code.split())
    st.markdown(f'<div style="text-align: center; margin: 5px 0;">{svg_code_oneline}</div>', unsafe_allow_html=True)

async def execute_search(query):
    # Use a container for the progress to avoid overwriting or shifting issues
    progress_container = st.empty()
    
    def on_progress(p):
        with progress_container.container():
             render_sword_progress(p)
            
    on_progress(0.0)
    products, logs = await run_scrapers_parallel(query, progress_callback=on_progress)
    on_progress(1.0)
    
    # Keep it visible for a moment
    await asyncio.sleep(0.8)
    progress_container.empty()
    return products, logs

# --- CATEGORY DEFINITIONS ---
CATEGORIES = {
    "Todos": [],
    "MOTU Origins": ["origins"],
    "Masterverse": ["masterverse", "revelation", "new eternia"],
    "Turtles of Grayskull": ["turtles", "tortugas"],
    "WWE Universe": ["wwe", "wrestling", "superstars"], 
    "Cartoon Collection": ["cartoon", "filmation"],
    "Snake Men": ["snake", "serpiente"],
    "Horda": ["horde", "horda"],
    "Transformers": ["transformers", "cybertron"],
    "Skeletor": ["skeletor"],
    "He-Man": ["he-man", "he man"]
}

# --- SIDEBAR (Secondary Filters) ---
with st.sidebar:
    # HEADER WITH CUSTOM ICON (Aligned with Flexbox)
    if os.path.exists("rueda_ajustes.png"):
        b64_icon = load_image_as_base64("rueda_ajustes.png")
        st.markdown(f"""
            <div style="display: flex; align-items: center; justify-content: flex-start; gap: 10px; margin-bottom: 20px;">
                <img src="data:image/png;base64,{b64_icon}" style="width: 40px; height: 40px; object-fit: contain;">
                <h1 style="margin: 0; padding: 0; font-size: 1.8rem; font-weight: 700; color: #fff;">Ajustes</h1>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.header("⚙️ Ajustes")
    
    st.markdown("**Tiendas Activas**")
    available_stores = ["ActionToys", "Fantasia Personajes", "Frikiverso", "Pixelatoy", "Electropolis"]
    selected_stores = []
    for store in available_stores:
        if st.checkbox(store, value=True, key=f"check_{store}"):
            selected_stores.append(store)
            
    st.divider()
    
    price_range = st.slider("Max Precio (€)", 0, 150, 150)
    sort_option = st.selectbox("Ordenar", ["Precio Ascendente", "Precio Descendente", "Nombre (A-Z)"])


# --- MAIN CONTENT ---
st.subheader("Elige Colección")
selected_category = st.selectbox("Categoría", list(CATEGORIES.keys()), index=0)

st.markdown("###") 
b_col1, b_col2, b_col3 = st.columns([1, 2, 1])
with b_col2:
    search_clicked = st.button("🔍 BUSCAR OFERTAS", type="primary", use_container_width=True)


# --- STATE MANAGEMENT ---
if 'scraped_results' not in st.session_state:
    st.session_state.scraped_results = []
if 'scraped_logs' not in st.session_state:
    st.session_state.scraped_logs = []
if 'has_searched' not in st.session_state:
    st.session_state.has_searched = False

if search_clicked:
    logs = []
    try:
        results, logs = asyncio.run(execute_search("masters of the universe"))
        st.session_state.scraped_results = results
        st.session_state.scraped_logs = logs
        st.session_state.has_searched = True
    except Exception as e:
        st.error(f"Error: {e}")

# --- RENDER RESULTS ---
if st.session_state.has_searched:
    results = st.session_state.scraped_results
    if not results:
        st.warning("No se encontraron resultados brutos.")
    else:
        # Convert to DF
        data = []
        for p in results:
            data.append({
                "Nombre": p.name,
                "PrecioVal": p.price_val,
                "PrecioDisplay": p.display_price,
                "Tienda": p.store_name,
                "Enlace": p.url,
                "Imagen": p.image_url,
                "NombreNorm": p.normalized_name
            })
        df = pd.DataFrame(data)
        
        # --- FILTERING ---
        keywords = CATEGORIES.get(selected_category, [])
        if keywords:
            pattern = '|'.join(keywords)
            df = df[df['Nombre'].str.contains(pattern, case=False, na=False)]
            
        if selected_stores:
            df = df[df['Tienda'].isin(selected_stores)]
        else:
             df = df.iloc[0:0] 
             
        df = df[df['PrecioVal'] <= price_range]
        
        # --- GROUPING ---
        final_items = []
        for name, group in df.groupby("NombreNorm"):
            best = group.sort_values("PrecioVal").iloc[0]
            valid_imgs = group['Imagen'].dropna()
            image_url = valid_imgs.iloc[0] if not valid_imgs.empty else "https://via.placeholder.com/150"
            
            final_items.append({
                "Nombre": best['Nombre'],
                "PrecioDisplay": best['PrecioDisplay'],
                "PrecioVal": best['PrecioVal'], # Added for sorting
                "Tienda": best['Tienda'],
                "Imagen": image_url,
                "Link": best['Enlace'],
                "Ofertas": len(group)
            })
            
        # --- SORTING (FIXED) ---
        # Sort the grouped items, not the dataframe (since grouping destroys order)
        if "Ascendente" in sort_option:
            final_items.sort(key=lambda x: x['PrecioVal'])
        elif "Descendente" in sort_option:
            final_items.sort(key=lambda x: x['PrecioVal'], reverse=True)
        else:
             final_items.sort(key=lambda x: x['Nombre'])

        st.success(f"Resultados para **{selected_category}**: {len(final_items)} figuras")
        
        html_cards = ""
        for item in final_items:
            badge = ""
            if item['Ofertas'] > 1:
                badge = f"<span style='background:#4CAF50;color:white;padding:2px 6px;border-radius:10px;font-size:0.7em;'>+{item['Ofertas']-1} tiendas</span>"
            
            card = f"""
<div class="product-card">
<div style="position:relative;">
<img src="{item['Imagen']}" class="product-img" loading="lazy">
<div style="position:absolute; top:0; right:0;">{badge}</div>
</div>
<div class="product-title">{item['Nombre']}</div>
<div class="price-row">
<span class="main-price">{item['PrecioDisplay']}</span>
<span class="store-badge">{item['Tienda']}</span>
</div>
<a href="{item['Link']}" target="_blank" class="action-btn">VER OFERTA</a>
</div>
"""
            html_cards += card
            
        st.markdown(f'<div class="product-grid">{html_cards}</div>', unsafe_allow_html=True)
        
        with st.expander("Ver Logs"):
            st.write(st.session_state.scraped_logs)
