import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from src.domain.models import ProductModel, CollectionItemModel, OfferModel, ScraperStatusModel, ScraperExecutionLogModel
from datetime import datetime, timedelta

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
    
    # Mission Control
    
    active_scrapers = db.query(ScraperStatusModel).filter(ScraperStatusModel.status == "running").all()
    
    # 1. Target Selector
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
            # Log spider_name usually "Electropolis", selection "Electropolis"
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
            if st.button("🔴 INICIAR ESCANEO", type="primary", use_container_width=True):
                import subprocess
                import sys
                # Use 'cmd /k' to KEEP THE WINDOW OPEN after execution/crash
                # structure: cmd.exe /k "python -m src.jobs.daily_scan args..."
                full_cmd = [sys.executable, "-m", "src.jobs.daily_scan"]
                if selected_shops:
                    full_cmd.append("--shops")
                    full_cmd.extend([s.lower() for s in selected_shops])
                
                # We need to pass the arguments correctly to cmd /c start "Title" cmd /k ...
                # Or simpler: just run cmd /k python ... directly in the new console
                final_flags = subprocess.CREATE_NEW_CONSOLE
                
                # Construct command list for cmd.exe
                # Note: We pass the separate arguments to avoid shell injection, 
                # but cmd /k expects the subsequent command. 
                # Ideally: ["cmd.exe", "/k", sys.executable, "-m", ...]
                cmd_wrapper = ["cmd.exe", "/k"] + full_cmd
                
                subprocess.Popen(cmd_wrapper, 
                                 cwd=str(img_dir.parent.parent.parent.parent),
                                 creationflags=final_flags)
                st.toast("🚀 Robots desplegados.")
                st.rerun()

    with col_ctrl2:
        if active_scrapers:
            # STOP BUTTON (Graceful)
            if st.button("🛑 DETENER (Suave)", type="secondary", key="stop_scan_btn", use_container_width=True):
                with open(".stop_scan", "w") as f:
                    f.write("STOP")
                st.toast("⛔ Señal enviada. Esperando al finalizar scraper actual...")

            # KILL SWITCH (Nuclear) or ZOMBIE CLEANUP
            if os.path.exists(".scan_pid"):
                if st.button("☢️ FORZAR CIERRE (Emergencia)", type="secondary", key="kill_scan_btn", use_container_width=True):
                    try:
                        with open(".scan_pid", "r") as f:
                            pid = int(f.read().strip())
                        import signal
                        os.kill(pid, signal.SIGTERM) # Try SIGTERM first
                        # On Windows os.kill only supports SIGTERM which acts as forceful kill
                        st.error(f"💀 Proceso {pid} eliminado.")
                        
                        # Cleanup DB status manually so UI unlocks
                        for s in active_scrapers:
                            s.status = "killed"
                        db.commit()
                        
                        # Cleanup files
                        if os.path.exists(".scan_pid"): os.remove(".scan_pid")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fallo al eliminar: {e}")
            else:
                 # ZOMBIE STATE: DB says running, but no PID file.
                 st.warning("⚠️ Estado Fantasma detectado (PID perdido).")
                 if st.button("🛠️ LIMPIEZA DE SISTEMA", help="Resetea el estado de la base de datos si el escáner murió inesperadamente."):
                     for s in active_scrapers:
                            s.status = "system_reset"
                     db.commit()
                     st.success("✅ Estado reseteado.")
                     st.rerun()

        else:
            st.info("Sistemas listos. Selecciona objetivos o lanza secuencia completa.")

    # 2. Live Logs (Admin Only)
    if user.role == "admin":
        st.divider()
        with st.expander("📡 Telemetría en Vivo (Admin)", expanded=True):
            log_file = "logs/oraculo.log"
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                        # Tail last 50 lines
                        lines = f.readlines()[-50:]
                        log_content = "".join(lines)
                    st.code(log_content, language="log")
                except Exception as e:
                    st.error(f"Error leyendo logs: {e}")
                
                # Auto-refresh button (poor man's websocket)
                if st.button("🔄 Actualizar Logs"):
                    st.rerun()
            else:
                st.warning("No hay logs disponibles aún.")

    # 3. Audit History
    st.divider() 
    st.markdown("### 📜 Auditoría de Ejecuciones")
    
    history_logs = db.query(ScraperExecutionLogModel).order_by(ScraperExecutionLogModel.start_time.desc()).limit(20).all()
    
    if history_logs:
        history_data = []
        for h in history_logs:
            duration = "En curso"
            if h.end_time and h.start_time:
                duration = str(h.end_time - h.start_time).split('.')[0]
                
            history_data.append({
                "Fecha": h.start_time.strftime("%d/%m %H:%M"),
                "Objetivo": h.spider_name,
                "Estado": "✅" if h.status in ["success", "completed"] else ("⚠️" if h.status == "success_empty" else "❌"),
                "Items": h.items_found,
                "Duración": duration,
                "Tipo": h.trigger_type
            })
            
        st.dataframe(
            pd.DataFrame(history_data),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.caption("No existen registros históricos aún.")
