import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from src.domain.models import ProductModel, CollectionItemModel, OfferModel, ScraperStatusModel

def render(db: Session, img_dir, user):
    # Header
    c1, c2 = st.columns([1, 8])
    with c1:
        st.image(str(img_dir / "Tablero.png"), use_container_width=True)
    with c2:
        st.markdown("# Tablero de Mando")
    
    current_user_id = user.id
    
    # Metrics
    total_products = db.query(ProductModel).count()
    # Count owned products via relationship (FILTERED BY USER)
    owned_products = (
        db.query(ProductModel)
        .join(CollectionItemModel)
        .filter(CollectionItemModel.owner_id == current_user_id)
        .count()
    )
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-label">Figuras en el Radar</div>
            <div class="metric-value">{total_products}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-label">En Mi Fortaleza</div>
            <div class="metric-value">{owned_products}</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
         # Placeholder for future "Best Deal" metric
         st.markdown(f"""
        <div class="glass-card">
            <div class="metric-label">Mejores Ofertas</div>
            <div class="metric-value">--</div> <small>Próximamente</small>
        </div>
        """, unsafe_allow_html=True)

    # Robot Stats
    st.markdown("### 🤖 Estado de los Robots")
    
    # Use pandas for quick stats (read-only safe)
    try:
        offers_df = pd.read_sql("SELECT shop_name, price, last_seen FROM offers", db.bind)
        
        if not offers_df.empty:
            c_stats1, c_stats2 = st.columns([2, 1])
            
            with c_stats1:
                st.caption("Ofertas detectadas por tienda")
                counts = offers_df['shop_name'].value_counts()
                st.bar_chart(counts, color="#00ff88")
                
            with c_stats2:
                st.caption("Resumen")
                st.dataframe(
                    counts, 
                    column_config={"shop_name": "Tienda", "count": "Figuras"},
                    use_container_width=True
                )
        else:
            st.info("No hay datos de scrapers aún.")
    except Exception as e:
        st.error(f"Error cargando estadísticas: {e}")

    # Mission Control
    st.divider()
    st.markdown("### 🚀 Control de Misión")
    
    active_scrapers = db.query(ScraperStatusModel).filter(ScraperStatusModel.status == "running").all()
    
    col_ctrl1, col_ctrl2 = st.columns([1, 3])
    with col_ctrl1:
        if active_scrapers:
            st.warning("⚠️ Escaneo en curso...")
        else:
            if st.button("🔴 INICIAR ESCANEO", type="primary", use_container_width=True):
                import subprocess
                # Run detached process
                subprocess.Popen(["python", "-m", "src.jobs.daily_scan"], 
                                 cwd=str(img_dir.parent.parent.parent.parent), # Go up to root? dashboard->views->web->src->ROOT
                                 # Actually app.py sets CWD usually. Let's rely on standard 'python -m' from root.
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
                st.toast("🚀 Robots desplegados. Monitorizando...")
                st.rerun()

    with col_ctrl2:
        if active_scrapers:
            st.info("Monitoriza el progreso en la barra lateral.")
        else:
            st.caption("Pulsa para iniciar una secuencia de escaneo manual con las nuevas estrategias de sigilo.")
