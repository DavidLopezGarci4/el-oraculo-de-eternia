import streamlit as st
import os
import sys
import subprocess
import signal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from src.domain.models import ProductModel, OfferModel, PendingMatchModel, BlackcludedItemModel, CollectionItemModel, UserModel, ScraperStatusModel, ScraperExecutionLogModel

def render_inline_product_admin(db: Session, p: ProductModel, current_user_id: int):
    """
    Renders the Superuser Edit Panel for a single product.
    Includes Metadata editing, nuclear options (Purge/Blacklist Product), and Offer management.
    """
    with st.expander(f"🛠️ Admin: {p.name}", expanded=False):
        # --- Metadata Editing ---
        c_meta1, c_meta2 = st.columns(2)
        with c_meta1:
            new_name = st.text_input("Nombre", p.name, key=f"edt_name_{p.id}")
            new_cat = st.text_input("Categoría", p.category, key=f"edt_cat_{p.id}")
        with c_meta2:
            new_img = st.text_input("URL Imagen", p.image_url, key=f"edt_img_{p.id}")
            
            if st.button("💾 Actualizar y Guardar", key=f"save_meta_{p.id}"):
                try:
                    target_p = db.query(ProductModel).filter(ProductModel.id == p.id).first()
                    if target_p:
                        target_p.name = new_name
                        target_p.category = new_cat
                        target_p.image_url = new_img
                        db.commit()
                        st.toast("Datos actualizados correctamente.")
                        st.rerun()
                    else:
                        st.error("El producto ya no existe.")
                except Exception as e:
                    db.rollback()
                    st.error(f"Error al guardar: {e}")

        st.divider()

        # --- Fusión / Migración ---
        st.write("🧬 **Fusión Molecular**")
        candidates = db.query(ProductModel).filter(ProductModel.id != p.id).order_by(ProductModel.name).all()
        
        if not candidates:
            st.warning("No hay otros productos con los cual fusionar.")
        else:
            c_merg1, c_merg2 = st.columns([3, 1])
            with c_merg1:
                selected_target = st.selectbox(
                    "Selecciona Destino",
                    options=candidates,
                    format_func=lambda x: f"{x.name} (ID: {x.id})",
                    key=f"sel_merge_{p.id}"
                )
            
            with c_merg2:
                st.write("") # Spacer
                if st.button("🔗 Fusionar", key=f"btn_merge_{p.id}"):
                    if not selected_target:
                        st.error("Debes seleccionar un destino.")
                    else:
                        target_id = selected_target.id
                        try:
                            target_p = db.query(ProductModel).filter(ProductModel.id == target_id).first()
                            current_p = db.query(ProductModel).filter(ProductModel.id == p.id).first()
                            
                            if target_p and current_p:
                                # Move Offers
                                for o in current_p.offers:
                                    o.product_id = target_id
                                
                                # Move Collection Items
                                c_items = db.query(CollectionItemModel).filter(CollectionItemModel.product_id == current_p.id).all()
                                for ci in c_items:
                                    exists = db.query(CollectionItemModel).filter(
                                        CollectionItemModel.owner_id == ci.owner_id, 
                                        CollectionItemModel.product_id == target_id
                                    ).first()
                                    if not exists:
                                        ci.product_id = target_id
                                    else:
                                        db.delete(ci)
                                
                                db.delete(current_p)
                                db.commit()
                                st.success(f"Fusionado con éxito en {target_p.name}.")
                                st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"Error en fusión: {e}")

        st.divider()

        # --- Nuclear Options ---
        st.write("☢️ **Zona de Peligro**")
        c_nuke1, c_nuke2 = st.columns(2)
        
        with c_nuke1:
            if st.button("🌪️ PURGAR", key=f"nuke_purg_{p.id}"):
                try:
                    target_p = db.query(ProductModel).filter(ProductModel.id == p.id).first()
                    if target_p:
                        for o in target_p.offers:
                            exists = db.query(PendingMatchModel).filter(PendingMatchModel.url == o.url).first()
                            if not exists:
                                pending = PendingMatchModel(
                                    scraped_name=target_p.name,
                                    price=o.price,
                                    currency=o.currency,
                                    url=o.url,
                                    shop_name=o.shop_name,
                                    image_url=target_p.image_url
                                )
                                db.add(pending)
                        
                        db.delete(target_p)
                        db.commit()
                        st.toast(f"Producto {p.name} desintegrado.")
                        st.rerun()
                except Exception as e:
                    db.rollback()
                    st.error(f"Error al purgar: {e}")

        with c_nuke2:
             if st.button("⛔ BLACKLIST", key=f"nuke_black_{p.id}"):
                try:
                    target_p = db.query(ProductModel).filter(ProductModel.id == p.id).first()
                    if target_p:
                        for o in target_p.offers:
                            exists = db.query(BlackcludedItemModel).filter(BlackcludedItemModel.url == o.url).first()
                            if not exists:
                                bl = BlackcludedItemModel(
                                    url=o.url,
                                    scraped_name=target_p.name,
                                    reason="admin_nuke_product"
                                )
                                db.add(bl)
                        db.delete(target_p)
                        db.commit()
                        st.toast(f"Producto {p.name} exiliado.")
                        st.rerun()
                except Exception as e:
                    db.rollback()
                    st.error(f"Error al exiliar: {e}")

        # --- Offer Management ---
        st.divider()
        st.caption("🔗 Gestión de Ofertas (Edición de Precios)")
        
        if not p.offers:
            st.info("Este producto no tiene ofertas vinculadas.")
        
        for o in p.offers:
            with st.container(border=True):
                c_head, c_btn = st.columns([4, 1])
                c_head.markdown(f"**{o.shop_name}**")
                
                # Edit Form
                c_edit1, c_edit2, c_edit3 = st.columns(3)
                
                new_price = c_edit1.number_input(
                    "Precio Actual (€)", 
                    min_value=0.0, 
                    value=float(o.price), 
                    step=0.01, 
                    format="%.2f",
                    key=f"edt_price_{o.id}"
                )
                
                new_hist = c_edit2.number_input(
                    "Mín. Histórico (€)", 
                    min_value=0.0, 
                    value=float(o.min_price), # Correct value based on request
                    step=0.01,
                    format="%.2f",
                    key=f"edt_min_{o.id}",
                    help="Precio mínimo histórico registrado."
                )

                new_max = c_edit3.number_input(
                    "Máx/Original (€)", 
                    min_value=0.0, 
                    value=float(o.max_price),
                    step=0.01,
                    format="%.2f",
                    key=f"edt_max_{o.id}",
                    help="Precio original o máximo registrado (Base para descuentos)."
                )
                
                # Save & Actions
                c_act1, c_act2, c_act3 = st.columns([1, 1, 1])
                
                if c_act1.button("💾 Guardar", key=f"save_offer_{o.id}"):
                    try:
                        target_o = db.query(OfferModel).filter(OfferModel.id == o.id).first()
                        if target_o:
                            target_o.price = new_price
                            target_o.min_price = new_hist
                            target_o.max_price = new_max
                            target_o.currency = "EUR" # Force currency as requested
                            db.commit()
                            st.toast("Precios actualizados.")
                            st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"Error: {e}")

                if c_act2.button("Unlink", key=f"adm_unlink_{o.id}"):
                     try:
                         target_o = db.query(OfferModel).filter(OfferModel.id == o.id).first()
                         if target_o:
                             exists = db.query(PendingMatchModel).filter(PendingMatchModel.url == target_o.url).first()
                             if not exists:
                                 pending = PendingMatchModel(
                                     scraped_name=p.name,
                                     price=target_o.price,
                                     currency=target_o.currency,
                                     url=target_o.url,
                                     shop_name=target_o.shop_name,
                                     image_url=p.image_url
                                 )
                                 db.add(pending)
                             db.delete(target_o)
                             db.commit()
                             st.toast("Desvinculado.")
                             st.rerun()
                     except Exception as e:
                         db.rollback()
                         st.error(f"Error: {e}")
                
                if c_act3.button("Ban", key=f"adm_ban_{o.id}"):
                    try:
                        target_o = db.query(OfferModel).filter(OfferModel.id == o.id).first()
                        if target_o:
                            # Check existence
                            exists = db.query(BlackcludedItemModel).filter(BlackcludedItemModel.url == target_o.url).first()
                            if not exists:
                                bl = BlackcludedItemModel(
                                    url=target_o.url,
                                    scraped_name=p.name,
                                    reason="admin_offer_ban"
                                )
                                db.add(bl)
                            db.delete(target_o)
                            db.commit()
                            st.toast("Baneado.")
                            st.rerun()
                    except Exception:
                        db.rollback()

def render_purgatory(db: Session, img_dir):
    # This view now serves as the main Consola de Administración
    c1, c2 = st.columns([1, 8])
    with c1:
        st.image(str(img_dir / "Purgatorio.png"), width="stretch")
    with c2:
        st.markdown("# Consola de Administración")
    
    st.markdown("---")
    
    # TABS structure
    tab_purg, tab_mission = st.tabs(["👻 Purgatorio (Ofertas)", "🚀 Control de Misión (Robots)"])
    
    with tab_purg:
        _render_purgatory_content(db)

    with tab_mission:
        _render_mission_control(db, img_dir)

def _render_mission_control(db, img_dir):
    st.subheader("📡 Centro de Operaciones")
    
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
            if st.button("🔴 INICIAR ESCANEO", type="primary", width="stretch", key="scan_go_admin"):
                import subprocess
                import sys
                full_cmd = [sys.executable, "-m", "src.jobs.daily_scan"]
                if selected_shops:
                    full_cmd.append("--shops")
                    full_cmd.extend([s.lower() for s in selected_shops])
                
                final_flags = subprocess.CREATE_NEW_CONSOLE
                cmd_wrapper = ["cmd.exe", "/k"] + full_cmd
                
                # Navigate up to root from web/static/images
                # C:\Users\dace8\OneDrive\Documentos\Antigravity\el-oraculo-de-eternia\src\web\static\images -> parents[3] is root
                root_cwd = img_dir.parent.parent.parent.parent
                
                subprocess.Popen(cmd_wrapper, 
                                 cwd=str(root_cwd),
                                 creationflags=final_flags)
                st.toast("🚀 Robots desplegados.")
                st.rerun()

    with col_ctrl2:
        if active_scrapers:
            if st.button("🛑 DETENER (Suave)", type="secondary", key="stop_scan_admin", width="stretch"):
                with open(".stop_scan", "w") as f:
                    f.write("STOP")
                st.toast("⛔ Señal enviada.")

            if os.path.exists(".scan_pid"):
                if st.button("☢️ FORZAR CIERRE (Emergencia)", type="secondary", key="kill_scan_admin", width="stretch"):
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
                 st.warning("⚠️ Estado Fantasma.")
                 if st.button("🛠️ LIMPIEZA DE SISTEMA", help="Resetea el estado de la base de datos si el escáner murió inesperadamente.", key="sys_reset_admin"):
                     for s in active_scrapers:
                            s.status = "system_reset"
                     db.commit()
                     st.success("✅ Estado reseteado.")
                     st.rerun()

        else:
            st.info("Sistemas listos.")

    # Live Logs
    st.divider()
    with st.expander("📝 Logs del Sistema", expanded=True):
        log_file = "logs/oraculo.log"
        if os.path.exists(log_file):
             if st.button("Actualizar Logs", key="refresh_logs_admin"): st.rerun()
             with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                 log_content = "".join(f.readlines()[-30:])
             st.code(log_content, language="log")

    # Execution History with Error Details
    st.divider()
    st.subheader("📚 Historial de Ejecuciones")
    
    from src.domain.models import ScraperExecutionLogModel
    history = db.query(ScraperExecutionLogModel).order_by(ScraperExecutionLogModel.start_time.desc()).limit(20).all()
    
    if history:
        for h in history:
            status_icon = "✅" if h.status in ["success", "completed"] else ("⚠️" if h.status == "success_empty" else "❌")
            with st.expander(f"{status_icon} {h.spider_name} - {h.start_time.strftime('%Y-%m-%d %H:%M')}"):
                c_h1, c_h2 = st.columns(2)
                c_h1.write(f"**Items:** {h.items_found}")
                c_h2.write(f"**Tipo:** {h.trigger_type}")
                
                if h.error_message:
                    st.error("Error Registrado:")
                    st.code(h.error_message, language="text")
    else:
        st.info("No hay historial disponible.")

def _render_purgatory_content(db):
    from src.core.matching import SmartMatcher
    matcher = SmartMatcher()
    
    # 1. Cargar catálogo para sugerencias (Cacheado por ejecución de renderizado)
    all_products = db.query(ProductModel).options(joinedload(ProductModel.offers)).all()
    
    # --- Controles Superiores ---
    st.subheader("🕵️ Buscador del Espejo")
    c_f1, c_f2 = st.columns([2, 1])
    with c_f1:
        purg_search = st.text_input("Filtrar almas por nombre...", key="purg_search", placeholder="Ej: He-Man...")
    with c_f2:
        shops = [r[0] for r in db.query(PendingMatchModel.shop_name).distinct().all()]
        sel_shops = st.multiselect("Filtrar por tienda", options=sorted(shops), key="purg_shops")

    st.divider()

    # --- Query con Filtros ---
    query = db.query(PendingMatchModel)
    if purg_search:
        query = query.filter(PendingMatchModel.scraped_name.ilike(f"%{purg_search}%"))
    if sel_shops:
        query = query.filter(PendingMatchModel.shop_name.in_(sel_shops))
    
    total_items = query.count()
    if total_items == 0:
        st.success("El Purgatorio está libre de esas almas. ¡Victoria!")
        return
    
    # --- Paginación ---
    PAGE_SIZE = 25 # Reducido para mejor rendimiento con SmartMatcher
    if "purgatory_page" not in st.session_state:
        st.session_state.purgatory_page = 0

    total_pages = (total_items - 1) // PAGE_SIZE + 1
    
    # Navigation
    c_pag1, c_pag2, c_pag3 = st.columns([1, 2, 1])
    with c_pag1:
        if st.button("⬅️ Anterior", disabled=(st.session_state.purgatory_page == 0), key="purg_prev"):
            st.session_state.purgatory_page -= 1
            st.rerun()
    with c_pag2:
        st.write(f"Página {st.session_state.purgatory_page + 1} de {total_pages} ({total_items} almas)")
    with c_pag3:
        if st.button("Siguiente ➡️", disabled=(st.session_state.purgatory_page >= total_pages - 1), key="purg_next"):
            st.session_state.purgatory_page += 1
            st.rerun()

    offset = st.session_state.purgatory_page * PAGE_SIZE
    pending_items = db.query(PendingMatchModel).offset(offset).limit(PAGE_SIZE).all()

    # --- Barra de Acciones en Bloque ---
    if "purgatory_selection" not in st.session_state:
        st.session_state.purgatory_selection = set()

    c_bulk1, c_bulk2, c_bulk3 = st.columns([1, 1, 1])
    with c_bulk1:
        if st.button("🔥 Descartar Seleccionados", type="secondary", use_container_width=True, disabled=not st.session_state.purgatory_selection):
            count = 0
            for item_id in list(st.session_state.purgatory_selection):
                item = db.query(PendingMatchModel).get(item_id)
                if item:
                    bl = BlackcludedItemModel(url=item.url, scraped_name=item.scraped_name, reason="bulk_purgatory_discard")
                    db.add(bl)
                    db.delete(item)
                    count += 1
            db.commit()
            st.session_state.purgatory_selection.clear()
            st.toast(f"Exiliadas {count} almas al olvido.")
            st.rerun()

    with c_bulk2:
        if st.button("🔗 Vínculo Automático (90%+)", type="primary", use_container_width=True):
            # Lógica para procesar toodo lo visible que tenga > 0.9 de confianza
            count = 0
            from src.infrastructure.repositories.product import ProductRepository
            repo = ProductRepository(db)
            for item in pending_items:
                # Re-match rápido
                m_best = None
                m_score = 0.0
                for p in all_products:
                    _, sc, _ = matcher.match(p.name, item.scraped_name, item.url)
                    if sc > m_score:
                        m_score = sc
                        m_best = p
                
                if m_best and m_score >= 0.9:
                    repo.add_offer(m_best, {
                        "shop_name": item.shop_name,
                        "price": item.price,
                        "currency": item.currency,
                        "url": item.url,
                        "is_available": True
                    })
                    db.delete(item)
                    count += 1
            db.commit()
            st.success(f"Vinculadas {count} ofertas de alta confianza.")
            st.rerun()

    with c_bulk3:
        if st.button("🧹 Limpiar Selección", use_container_width=True):
            st.session_state.purgatory_selection.clear()
            st.rerun()

    st.divider()

    # Group controls
    for item in pending_items:
        # Lógica de Sugerencia Inteligente
        best_match = None
        best_score = 0.0
        
        # Solo buscamos sugerencias si hay productos y es la página actual (ahorro CPU)
        for p in all_products:
            is_m, score, _ = matcher.match(p.name, item.scraped_name, item.url)
            if score > best_score:
                best_score = score
                best_match = p
        
        col_select, col_expander = st.columns([0.1, 9.9])
        
        with col_select:
            is_selected = item.id in st.session_state.purgatory_selection
            if st.checkbox("Select", value=is_selected, key=f"sel_{item.id}", label_visibility="collapsed"):
                st.session_state.purgatory_selection.add(item.id)
            else:
                st.session_state.purgatory_selection.discard(item.id)

        with col_expander:
            with st.expander(f"{item.scraped_name} - {item.shop_name} ({item.price}€)", expanded=(best_score > 0.8)):
                if item.image_url:
                    st.image(item.image_url, width=100)
                
                if best_match:
                    st.info(f"🎯 **Sugerencia del Oráculo:** {best_match.name} (Confianza: {best_score:.2%})")
                
                from src.web.shared import render_external_link
                render_external_link(item.url, "Abrir Enlace", key_suffix=f"purg_{item.id}")
                
                c1, c2, c3 = st.columns([2, 1, 1])
            
            # Match
            from src.infrastructure.repositories.product import ProductRepository
            repo = ProductRepository(db)
            
            # Selection con sugerencia por defecto
            idx_suggestion = 0
            if best_match:
                try:
                    idx_suggestion = all_products.index(best_match)
                except ValueError: pass

            target_p = c1.selectbox("Vincular a:", all_products, index=idx_suggestion, format_func=lambda x: x.name, key=f"purg_sel_{item.id}")
            
            if c2.button("✅ Vincular", key=f"purg_ok_{item.id}"):
                if target_p:
                    # RE-FETCH to attach to current session
                    fresh_p = db.query(ProductModel).filter(ProductModel.id == target_p.id).first()
                    if fresh_p:
                        repo.add_offer(fresh_p, {
                            "shop_name": item.shop_name,
                            "price": item.price,
                            "currency": item.currency,
                            "url": item.url,
                            "is_available": True
                        })
                        db.delete(item)
                        db.commit()
                        st.toast("Vinculado.")
                        st.rerun()
                    else:
                        st.error("Producto no encontrado.")
            
            if c3.button("🔥 Descartar", key=f"purg_del_{item.id}"):
                # Blacklist
                bl = BlackcludedItemModel(url=item.url, scraped_name=item.scraped_name, reason="purgatory_discard")
                db.add(bl)
                db.delete(item)
                db.commit()
                st.toast("Descartado.")
                st.rerun()
