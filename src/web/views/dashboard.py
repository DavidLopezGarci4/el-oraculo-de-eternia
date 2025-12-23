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

    # Mission Control (Real-time checks, no cache for active status)
    st.divider()
    st.markdown("### 🚀 Control de Misión")
    
    active_scrapers = db.query(ScraperStatusModel).filter(ScraperStatusModel.status == "running").all()
    
    # Target Selector
    import os
    selected_shops = st.multiselect(
        "Objetivos de Escaneo",
        options=["ActionToys", "Fantasia", "Frikiverso", "Pixelatoy", "Electropolis"],
        default=[],
        placeholder="Todos los objetivos (Por defecto)",
        disabled=bool(active_scrapers)
    )
    
    # Cooldown Check
    hot_targets = []
    if selected_shops:
        cutoff = datetime.utcnow() - timedelta(hours=20)
        recent_logs = db.query(ScraperExecutionLogModel).filter(
            ScraperExecutionLogModel.start_time > cutoff
        ).all()
        
        for log in recent_logs:
            # Map log spider_name to selection (fuzzy or exact)
            for shop in selected_shops:
                if shop.lower() in log.spider_name.lower():
                    hot_targets.append((shop, log.end_time))
                    
    if hot_targets:
        st.warning(f"⚠️ ¡Precaución! Objetivos calientes (escaneados < 24h): {', '.join([t[0] for t in hot_targets])}. Riesgo de baneo.")
    
    col_ctrl1, col_ctrl2 = st.columns([1, 1])
    with col_ctrl1:
        if active_scrapers:
            st.warning("⚠️ Escaneo en curso...")
            st.caption(f"Operativo: {[s.spider_name for s in active_scrapers]}")
        else:
            if st.button("🔴 INICIAR ESCANEO", type="primary", width="stretch"):
                import subprocess
                import sys
                full_cmd = [sys.executable, "-m", "src.jobs.daily_scan"]
                if selected_shops:
                    full_cmd.append("--shops")
                    full_cmd.extend([s.lower() for s in selected_shops])
                
                final_flags = subprocess.CREATE_NEW_CONSOLE
                cmd_wrapper = ["cmd.exe", "/k"] + full_cmd
                
                subprocess.Popen(cmd_wrapper, 
                                 cwd=str(img_dir.parent.parent.parent.parent),
                                 creationflags=final_flags)
                st.toast("🚀 Robots desplegados.")
                st.rerun()

    with col_ctrl2:
        if active_scrapers:
            if st.button("🛑 DETENER (Suave)", type="secondary", key="stop_scan_btn", width="stretch"):
                with open(".stop_scan", "w") as f:
                    f.write("STOP")
                st.toast("⛔ Señal enviada. Esperando al finalizar scraper actual...")

            if os.path.exists(".scan_pid"):
                if st.button("☢️ FORZAR CIERRE (Emergencia)", type="secondary", key="kill_scan_btn", width="stretch"):
                    try:
                        with open(".scan_pid", "r") as f:
                            pid = int(f.read().strip())
                        import signal
                        os.kill(pid, signal.SIGTERM) 
                        st.error(f"💀 Proceso {pid} eliminado.")
                        
                        for s in active_scrapers:
                            s.status = "killed"
                        db.commit()
                        if os.path.exists(".scan_pid"): os.remove(".scan_pid")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fallo al eliminar: {e}")
            else:
                 st.warning("⚠️ Estado Fantasma detectado (PID perdido).")
                 if st.button("🛠️ LIMPIEZA DE SISTEMA", help="Resetea el estado de la base de datos si el escáner murió inesperadamente."):
                     for s in active_scrapers:
                            s.status = "system_reset"
                     db.commit()
                     st.success("✅ Estado reseteado.")
                     st.rerun()

        else:
            st.info("Sistemas listos. Selecciona objetivos o lanza secuencia completa.")

    # Live Logs (Admin Only) - No Cache needed (It's text file read)
    if user.role == "admin":
        st.divider()
        with st.expander("📡 Telemetría en Vivo (Admin)", expanded=True):
            log_file = "logs/oraculo.log"
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()[-50:]
                        log_content = "".join(lines)
                    st.code(log_content, language="log")
                except Exception as e:
                    st.error(f"Error leyendo logs: {e}")
                
                if st.button("🔄 Actualizar Logs"):
                    st.rerun()
            else:
                st.warning("No hay logs disponibles aún.")

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
