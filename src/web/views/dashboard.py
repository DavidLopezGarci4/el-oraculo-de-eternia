import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from src.domain.models import ProductModel, CollectionItemModel, OfferModel, ScraperStatusModel, ScraperExecutionLogModel
from datetime import datetime, timedelta

def render(db: Session, img_dir, user):
    # Header
    c1, c2 = st.columns([1, 8])
    with c1:
        st.image(str(img_dir / "Tablero.png"), width="stretch")
    with c2:
        st.markdown("# Tablero de Mando")
    
    # Optimized Data Fetching
    # Metrics are fast (COUNT queries), so we don't cache them to ensure immediate updates after adding items.
    def get_main_metrics(_user_id):
        # Note: _user_id is underscore to avoid hashing issues if object, but int is fine.
        from src.infrastructure.database import SessionLocal
        with SessionLocal() as session:
            total = session.query(ProductModel).count()
            owned = (
                session.query(ProductModel)
                .join(CollectionItemModel)
                .filter(CollectionItemModel.owner_id == _user_id)
                .count()
            )
            return total, owned

    @st.cache_data(ttl=300)
    def get_offers_overview():
        from src.infrastructure.database import engine
        try:
            return pd.read_sql("SELECT shop_name, price, last_seen FROM offers", engine)
        except Exception:
            return pd.DataFrame()

    @st.cache_data(ttl=60)
    def get_history_log():
        from src.infrastructure.database import SessionLocal
        with SessionLocal() as session:
            history = session.query(ScraperExecutionLogModel).order_by(ScraperExecutionLogModel.start_time.desc()).limit(20).all()
            # Convert to list of dicts for caching
            data = []
            for h in history:
                duration = "En curso"
                if h.end_time and h.start_time:
                    duration = str(h.end_time - h.start_time).split('.')[0]
                data.append({
                    "Fecha": h.start_time.strftime("%d/%m %H:%M"),
                    "Objetivo": h.spider_name,
                    "Estado": "✅" if h.status in ["success", "completed"] else ("⚠️" if h.status == "success_empty" else "❌"),
                    "Items": h.items_found,
                    "Duración": duration,
                    "Tipo": h.trigger_type
                })
            return data

    current_user_id = user.id
    
    # 1. Metrics
    total_products, owned_products = get_main_metrics(current_user_id)
    
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

    # 2. Robot Stats
    st.markdown("### 🤖 Estado de los Robots")
    
    offers_df = get_offers_overview()
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
                width="stretch"
            )
    else:
        st.info("No hay datos de scrapers aún.")

    # Mission Control has been moved to Admin Console.
    # We only show a small subtle indicator if scanning is active.
    active_scrapers = db.query(ScraperStatusModel).filter(ScraperStatusModel.status == "running").all()
    if active_scrapers:
        st.divider()
        st.info(f"🔄 **Sistemas Activos:** {len(active_scrapers)} operación(es) en curso.")



    # 3. Audit History
    st.divider() 
    st.markdown("### 📜 Auditoría de Ejecuciones")
    
    history_data = get_history_log()
    
    if history_data:
        st.dataframe(
            pd.DataFrame(history_data),
            width="stretch",
            hide_index=True
        )
    else:
        st.caption("No existen registros históricos aún.")
