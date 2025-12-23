import sys
import os
from pathlib import Path

# Add project root to Python path
root_path = Path(__file__).resolve().parent.parent.parent
IMG_DIR = root_path / "src" / "web" / "static" / "images"
sys.path.append(str(root_path))

import streamlit as st
from sqlalchemy import text
from src.infrastructure.database import SessionLocal, init_db, engine
from src.infrastructure.repositories.product import ProductRepository
from src.domain.models import UserModel, ScraperStatusModel
from src.core.security import verify_password, hash_password

# --- Views ---
from src.web.views import dashboard, catalog, hunter, collection, admin, config

# --- Configuration & Theme ---
st.set_page_config(
    page_title="El Oráculo de Eternia",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize DB (Create tables if new models added)
init_db()

# --- AUTO-MIGRATION (Hotfix) ---
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE scraper_status ADD COLUMN progress INTEGER DEFAULT 0"))
        conn.commit()
except Exception:
    # Column likely exists
    pass
# -------------------------------

# Custom CSS for Glassmorphism
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        background-image: linear-gradient(315deg, #0e1117 0%, #1a1d24 74%);
    }
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.18);
        padding: 20px;
        margin-bottom: 20px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #00ff88;
        text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
    }
    .metric-label {
        font-size: 0.9rem;
        color: #a0a0a0;
    }
    
    /* Sidebar Links Style - Compact */
    [data-testid="stSidebar"] .stButton button {
        width: 100%;
        border: none;
        background: transparent;
        text-align: left !important;
        display: flex;
        justify-content: flex-start;
        color: #e0e0e0;
        padding: 0.25rem 0.5rem; /* Reduced padding (Shorter) */
        font-size: 0.95rem; /* Slightly smaller text */
        line-height: 1.2;
        min_height: auto;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: rgba(41, 128, 185, 0.1);
        color: #ffffff;
        border-radius: 5px;
    }
    [data-testid="stSidebar"] div[data-testid="column"] {
        padding: 0 !important; /* Remove column gaps */
    }
</style>
<link rel="manifest" href="manifest.json">
<script>
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', function() {
        navigator.serviceWorker.register('sw.js');
      });
    }
</script>
""", unsafe_allow_html=True)

# --- Database Connection ---
def get_db_session():
    # No cache_resource here (Session Isolation Fix)
    return SessionLocal()

db = get_db_session()
repo = ProductRepository(db)

# --- Sidebar ---
with st.sidebar:
    logo_path = str(IMG_DIR / "Masters_Oraculo_Logo.png")
    # Center Image using columns
    col_l, col_c, col_r = st.columns([1, 4, 1])
    with col_c:
        st.image(logo_path, width="stretch")
    
    # --- Auth & Session ---
    if "role" not in st.session_state:
        st.session_state.role = "viewer"
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "user" not in st.session_state:
        st.session_state.user = None

    def login_form():
        with st.sidebar.expander("🔐 Acceso Guardián", expanded=True):
            user_input = st.text_input("Usuario")
            pwd_input = st.text_input("Contraseña", type="password")
            if st.button("Entrar"):
                # DB Auth
                user = db.query(UserModel).filter(UserModel.username == user_input).first()
                if user and verify_password(pwd_input, user.hashed_password):
                    st.session_state.authenticated = True
                    st.session_state.role = user.role
                    st.session_state.username = user.username
                    st.session_state.user = user
                    st.success(f"¡Bienvenido, {user.username}!")
                    st.rerun()
                elif user_input == "admin" and pwd_input == "eternia":
                     # Fallback first time init
                     if db.query(UserModel).count() == 0:
                         st.session_state.authenticated = True
                         st.session_state.role = "admin"
                         st.session_state.username = "admin"
                         from types import SimpleNamespace
                         st.session_state.user = SimpleNamespace(id=0, username="admin", role="admin", email="")
                         st.warning("Acceso de Emergencia.")
                         st.rerun()
                     else:
                         st.error("Acceso de emergencia deshabilitado.")
                else:
                    st.error("Credenciales inválidas.")

    def logout():
        st.session_state.authenticated = False
        st.session_state.role = "viewer"
        st.session_state.username = None
        st.session_state.user = None
        st.rerun()
        
    # --- Sidebar: Robot Status ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("---")
    # Header with Icon
    c_mirror_icon, c_mirror_lbl = st.sidebar.columns([1.2, 3.8], vertical_alignment="center")
    with c_mirror_icon:
        st.image(str(IMG_DIR / "mini_espejo.png"), width=63)
    with c_mirror_lbl:
        st.markdown("**Espejo de los Espíritus**")
        
    # Optimized Sidebar Status with Caching
    @st.cache_data(ttl=60)
    def get_sidebar_status():
        # Use a new session for thread safety in cache
        from src.infrastructure.database import SessionLocal
        with SessionLocal() as session:
            active = session.query(ScraperStatusModel).filter(ScraperStatusModel.status == "running").all()
            # Convert to dict to be picklable/cacheable if needed, or just return objects (detached)
            # returning simple data structures is safer for st.cache_data
            active_data = [{"spider_name": s.spider_name, "progress": s.progress} for s in active]
            
            last = session.query(ScraperStatusModel).order_by(ScraperStatusModel.last_update.desc()).first()
            last_data = {"spider_name": last.spider_name, "status": last.status} if last else None
            return active_data, last_data

    active_scrapers_data, last_run_data = get_sidebar_status()
    
    if active_scrapers_data:
        # Calculate Total Progress (Average of all running)
        total_p = sum([s["progress"] for s in active_scrapers_data]) / len(active_scrapers_data) if active_scrapers_data else 0
        total_p = int(total_p)
        
        # Radioactive Sword SVG Implementation
        import base64
        sword_path = IMG_DIR / "espada_limpia.svg"
        if sword_path.exists():
            with open(sword_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            
            b64_sword = base64.b64encode(svg_content.encode('utf-8')).decode("utf-8")
            sword_url = f"data:image/svg+xml;base64,{b64_sword}"
            
            st.sidebar.markdown(f"""
            <div style="position: relative; width: 100%; height: 300px; display: flex; justify-content: center; align-items: center; margin-bottom: 20px;">
                <!-- Base Ghost Sword -->
                <div style="
                    position: absolute;
                    width: 100%;
                    height: 100%;
                    background-image: url('{sword_url}');
                    background-size: contain;
                    background-repeat: no-repeat;
                    background-position: center;
                    opacity: 0.1;
                    filter: grayscale(100%);
                "></div>
                
                <!-- Radioactive Filler Sword -->
                <div style="
                    position: absolute;
                    width: 100%;
                    height: 100%;
                    background-image: url('{sword_url}');
                    background-size: contain;
                    background-repeat: no-repeat;
                    background-position: center;
                    clip-path: inset({100 - total_p}% 0 0 0);
                    transition: clip-path 0.5s ease-in-out;
                    filter: drop-shadow(0 0 15px #00ffff) drop-shadow(0 0 30px #00aaff) brightness(1.5);
                "></div>
                
                <!-- Percentage Text -->
                 <div style="
                    position: absolute;
                    bottom: 0;
                    width: 100%;
                    text-align: center;
                    font-family: 'Arial', sans-serif;
                    font-weight: bold;
                    font-size: 24px;
                    color: #fff;
                    text-shadow: 0 0 10px #00ffff;
                ">
                    {total_p}%
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            for s in active_scrapers_data:
                 st.sidebar.caption(f"⚡ Cargando: {s['spider_name']}...")
        else:
             st.sidebar.warning("Espada rota (SVG no encontrado)")
    else:
        if last_run_data:
             st.sidebar.caption(f"Última: {last_run_data['spider_name']} ({last_run_data['status']})")

    st.sidebar.markdown("---")
    
    # --- SCROLL TO TOP ON NAV ---
    # Inject simple JS to force scroll to top when rendering top of sidebar/app
    components_t = """
    <script>
        window.scrollTo(0, 0);
    </script>
    """
    st.components.v1.html(components_t, height=0, width=0)
    if st.session_state.role == "admin":
        if st.sidebar.button("🧹 Limpiar Caché", help="Refrescar memoria del sistema"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.toast("✨ Caché purgada. El sistema está fresco.")
            st.rerun()

    # --- Navigation ---
    if "page" not in st.session_state:
        st.session_state.page = "Tablero"
        
    st.sidebar.markdown("### Navegación")
    
    menu_items = [
        {"id": "Tablero", "label": "Tablero", "icon": "mini_tablero.png"},
        {"id": "Catalogo", "label": "Catálogo", "icon": "Catalogo.png"},
        {"id": "Cazador", "label": "🔥 Cazador", "icon": "mini_cazador_ofertas.png"},
        {"id": "Coleccion", "label": "Mi Colección", "icon": "Mi_Coleccion.png"}
    ]
    
    if st.session_state.role == "admin":
        menu_items.extend([
            {"id": "Purgatorio", "label": "Purgatorio", "icon": "Purgatorio.png"},
            {"id": "Configuracion", "label": "Configuración", "icon": "Configuracion.png"}
        ])
    
    for item in menu_items:
        # Use tighter columns: Icon (1) | Button (5) -> Icon (1.5) | Button (5.5) but with CSS adjustment
        # Actually in Streamlit, columns are flex. [1, 4] is standard.
        # Let's try [1, 4] to bring text closer to icon.
        c_icon, c_btn = st.sidebar.columns([1, 4], vertical_alignment="center")
        with c_icon:
            # Center icon in its small column
            st.image(str(IMG_DIR / item["icon"]), width=22) # Slightly smaller icon
        with c_btn:
             # Custom CSS class for button alignment if needed, but 'stretch' fills the col.
             is_active = st.session_state.page == item["id"]
             if st.button(item["label"], key=f"nav_{item['id']}", type="primary" if is_active else "secondary", width="stretch"):
                 st.session_state.page = item["id"]
                 st.rerun()

    if not st.session_state.authenticated:
        login_form()
    else:
        st.sidebar.markdown("---")
        # User Profile as a row
        c_usr_icon, c_usr_info = st.sidebar.columns([1, 4], vertical_alignment="center")
        with c_usr_icon:
             st.write("👤")
        with c_usr_info:
             st.caption(f"{st.session_state.username}")
             
        if st.sidebar.button("🔓 Salir", on_click=logout, width="stretch"):
            pass
    
    st.sidebar.markdown("---")
    st.sidebar.caption("v2.6 Polished UI")


# --- ROUTER ---
# Ensure user is fully loaded in session object for views
user = st.session_state.get("user")

if st.session_state.authenticated and user:
    try:
        page = st.session_state.page
        
        if page == "Tablero":
            dashboard.render(db, IMG_DIR, user)
        elif page == "Catalogo":
            catalog.render(db, IMG_DIR, user, repo)
        elif page == "Cazador":
            hunter.render(db, IMG_DIR, user, repo)
        elif page == "Coleccion":
            collection.render(db, IMG_DIR, user)
        elif page == "Purgatorio":
            # Admin check
            if user.role == "admin":
                admin.render_purgatory(db, IMG_DIR)
            else:
                st.error("Zona restringida.")
        elif page == "Configuracion":
            if user.role == "admin":
                config.render(db, user, IMG_DIR)
            else:
                st.error("Zona restringida.")
        else:
            dashboard.render(db, IMG_DIR, user)
            
    except Exception as e:
        st.error(f"Error en la aplicación: {e}")
        st.exception(e) # Show stack trace for debug
else:
    # Landing / Not Authenticated
    # Landing / Not Authenticated
    st.info("Por favor, inicia sesión en la barra lateral para acceder a los secretos de Grayskull.")
    
    # Center Landing Image
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.image(str(IMG_DIR / "Oraculo_Eternia.png"), width="stretch")

# Close DB
db.close()
