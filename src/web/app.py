import sys
import os
from pathlib import Path

# Add project root to Python path
root_path = Path(__file__).resolve().parent.parent.parent
IMG_DIR = root_path / "src" / "web" / "static" / "images"
sys.path.append(str(root_path))

import streamlit as st
from src.infrastructure.database import SessionLocal
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
    
    /* Sidebar Links Style */
    [data-testid="stSidebar"] .stButton button {
        width: 100%;
        border: none;
        background: transparent;
        text-align: left !important;
        display: flex;
        justify-content: flex-start;
        color: #e0e0e0;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: rgba(41, 128, 185, 0.1);
        color: #ffffff;
    }
    [data-testid="stSidebar"] .stButton button[kind="primary"] {
        background-color: rgba(41, 128, 185, 0.15);
        color: #3498db;
        border-left: 2px solid #3498db;
    }
    [data-testid="stSidebar"] .stButton button:focus {
        box-shadow: none;
        outline: none;
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
        st.image(logo_path, use_container_width=True)
    
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
    st.sidebar.markdown("### 🪞 Espejo de los Espíritus")
    active_scrapers = db.query(ScraperStatusModel).filter(ScraperStatusModel.status == "running").all()
    
    if active_scrapers:
        for s in active_scrapers:
            st.sidebar.info(f"🔄 {s.spider_name}: Ejecutando...")
            st.sidebar.progress(50)
    else:
        last_run = db.query(ScraperStatusModel).order_by(ScraperStatusModel.last_update.desc()).first()
        if last_run:
             st.sidebar.caption(f"Última: {last_run.spider_name} ({last_run.status})")
             
    st.sidebar.markdown("---")

    # --- Navigation ---
    if "page" not in st.session_state:
        st.session_state.page = "Tablero"
        
    st.sidebar.markdown("### Navegación")
    
    menu_items = [
        {"id": "Tablero", "label": "Tablero", "icon": "Tablero.png"},
        {"id": "Catalogo", "label": "Catálogo", "icon": "Catalogo.png"},
        {"id": "Cazador", "label": "🔥 Cazador", "icon": "Catalogo.png"},
        {"id": "Coleccion", "label": "Mi Colección", "icon": "Mi_Coleccion.png"}
    ]
    
    if st.session_state.role == "admin":
        menu_items.extend([
            {"id": "Purgatorio", "label": "Purgatorio", "icon": "Purgatorio.png"},
            {"id": "Configuracion", "label": "Configuración", "icon": "Configuracion.png"}
        ])
    
    for item in menu_items:
        c_icon, c_btn = st.sidebar.columns([1, 5], vertical_alignment="center")
        with c_icon:
            st.image(str(IMG_DIR / item["icon"]), width=25)
        with c_btn:
            is_active = st.session_state.page == item["id"]
            if st.button(item["label"], key=f"nav_{item['id']}", type="primary" if is_active else "secondary", use_container_width=True):
                st.session_state.page = item["id"]
                st.rerun()

    if not st.session_state.authenticated:
        login_form()
    else:
        st.sidebar.markdown("---")
        st.sidebar.caption(f"👤 {st.session_state.username}")
        st.sidebar.button("🔓 Cerrar Sesión", on_click=logout)
    
    st.sidebar.markdown("---")
    st.sidebar.caption("v2.5 Refactored")


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
        st.image(str(IMG_DIR / "Oraculo_Eternia.png"), use_container_width=True)

# Close DB
db.close()
