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
    @st.cache_data(ttl=60)
    def get_main_metrics(_user_id):
        # Note: _user_id is underscored to prevent hashing issues but int is safe.
        # We re-instantiate session to be thread-safe inside the cache
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

    @st.cache_data(ttl=10) # Lower TTL to see immediate changes
    def get_history_log():
        from src.infrastructure.database import SessionLocal
        with SessionLocal() as session:
            # Fetch last 50 to give more context
            history = session.query(ScraperExecutionLogModel).order_by(ScraperExecutionLogModel.start_time.desc()).limit(50).all()
            data = []
            for h in history:
                duration = "En curso"
                if h.end_time and h.start_time:
                    duration = str(h.end_time - h.start_time).split('.')[0]
                
                # Determine status icon
                icon = "✅"
                if h.status == "success_empty":
                    icon = "⚠️"
                elif h.status == "error":
                    icon = "❌" # Cross mark
                elif h.status == "running":
                    icon = "🔄"
                
                data.append({
                    "ID": h.id, # Hidden key
                    "Fecha": h.start_time.strftime("%d/%m %H:%M"),
                    "Objetivo": h.spider_name,
                    "Estado": icon,
                    "Items": h.items_found,
                    "Duración": duration,
                    "Tipo": h.trigger_type,
                    "Error": h.error_message, # Hidden detail
                    "StatusRaw": h.status
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
        # Normalización Visual Definitiva (KAIZEN) using shared helper
        from src.web.shared import normalize_shop_name
        offers_df['shop_name'] = offers_df['shop_name'].map(lambda x: normalize_shop_name(x, mode="visual"))
        
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

    # 3. Audit History & Inspector
    st.divider() 
    c_hist_title, c_hist_refresh = st.columns([8, 1])
    with c_hist_title:
        st.markdown("### 📜 Auditoría de Ejecuciones")
    with c_hist_refresh:
        if st.button("↻"):
            get_history_log.clear()
            st.rerun()
    
    history_data = get_history_log()
    
    if history_data:
        df_hist = pd.DataFrame(history_data)
        
        # Display main table (excluding detailed error column)
        st.dataframe(
            df_hist[["Fecha", "Objetivo", "Estado", "Items", "Duración", "Tipo"]],
            width="stretch",
            hide_index=True
        )
        
        st.markdown("#### 🕵️ Inspector de Logs")
        
        # Selector for detailed view
        # Create a label for selection
        options = {f"{row['ID']} - {row['Objetivo']} ({row['Fecha']})": row for row in history_data}
        selected_label = st.selectbox("Selecciona una ejecución para ver detalles:", list(options.keys()))
        
        if selected_label:
            details = options[selected_label]
            is_error = details["StatusRaw"] == "error"
            is_warning = details["StatusRaw"] == "success_empty"
            
            # Status Banner
            if is_error:
                st.error(f"❌ La ejecución falló después de {details['Duración']}")
            elif is_warning:
                st.warning(f"⚠️ La ejecución finalizó correctamente pero NO encontró items (0 encontrados).")
            else:
                st.success(f"✅ Ejecución exitosa. {details['Items']} items procesados.")
            
            # Error Message View
            if is_error and details["Error"]:
                with st.expander("🔍 Ver Traceback / Mensaje de Error", expanded=True):
                    st.code(details["Error"], language="python")
            elif is_warning:
                st.info("ℹ️ **Diagnóstico de Warning:**\n"
                        "- El scraper funcionó técnicamente (login/navegación ok) pero no extrajo datos.\n"
                        "- **Posibles causas:** Selectores CSS obsoletos, cambios en la web destino, o simplemente no hay stock/novedades.\n"
                        "- Revisa si la web ha cambiado su diseño recientemente.")
    else:
        st.caption("No existen registros históricos aún.")
