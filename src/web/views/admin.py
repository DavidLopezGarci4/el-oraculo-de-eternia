import streamlit as st
import os
import sys
import subprocess
import signal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload

def render_inline_product_admin(db: Session, p, current_user_id: int):
    from src.domain.models import ProductModel, OfferModel, CollectionItemModel, PendingMatchModel, BlackcludedItemModel
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
                                all_data = {
                                    "scraped_name": target_p.name,
                                    "price": o.price,
                                    "currency": o.currency,
                                    "url": o.url,
                                    "shop_name": o.shop_name,
                                    "image_url": target_p.image_url
                                }
                                from sqlalchemy import inspect
                                mapper = inspect(PendingMatchModel)
                                allowed_keys = {c.key for c in mapper.attrs}
                                pending_data = {k: v for k, v in all_data.items() if k in allowed_keys}
                                
                                pending = PendingMatchModel(**pending_data)
                                db.add(pending)
                        
                        db.delete(target_p)
                        db.commit()
                        
                        # LOG HISTORY: PURGE
                        try:
                            from src.domain.models import OfferHistoryModel
                            for o in target_p.offers:
                                history = OfferHistoryModel(
                                    offer_url=o.url,
                                    product_name=target_p.name,
                                    shop_name=o.shop_name,
                                    price=o.price,
                                    action_type="PURGED",
                                    details=f"Product '{target_p.name}' purged by admin."
                                )
                                db.add(history)
                            db.commit()
                        except: pass
                        
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
                                 all_data = {
                                     "scraped_name": p.name,
                                     "price": target_o.price,
                                     "currency": target_o.currency,
                                     "url": target_o.url,
                                     "shop_name": target_o.shop_name,
                                     "image_url": p.image_url
                                 }
                                 from sqlalchemy import inspect
                                 mapper = inspect(PendingMatchModel)
                                 allowed_keys = {c.key for c in mapper.attrs}
                                 pending_data = {k: v for k, v in all_data.items() if k in allowed_keys}

                                 pending = PendingMatchModel(**pending_data)
                                 db.add(pending)
                             db.delete(target_o)
                             db.commit()
                             
                             # LOG HISTORY: UNLINKED
                             try:
                                 from src.domain.models import OfferHistoryModel
                                 history = OfferHistoryModel(
                                     offer_url=target_o.url,
                                     product_name=p.name,
                                     shop_name=target_o.shop_name,
                                     price=target_o.price,
                                     action_type="UNLINKED",
                                     details=f"Unlinked from product '{p.name}' by admin."
                                 )
                                 db.add(history)
                                 db.commit()
                             except: pass
                             
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
    # This view now serves as the main El Espejo de los Espíritus (Purgatorio)
    c1, c2 = st.columns([1, 8])
    with c1:
        st.image(str(img_dir / "Purgatorio.png"), width="stretch")
    with c2:
        st.markdown("# El Espejo de los Espíritus (Purgatorio)")
    
    st.markdown("---")
    
    # TABS structure
    tab_purg, tab_mission, tab_history, tab_bunker = st.tabs([
        "Purgatorio (Ofertas)", 
        "Control de Misión (Robots)", 
        "📜 Historial de Almas",
        "🏰 La Cámara de Grayskull (Búnker)"
    ])
    
    with tab_purg:
        _render_purgatory_content(db)

    with tab_mission:
        _render_mission_control(db, img_dir)
        
    with tab_history:
        _render_bastion_history(db)
        
    with tab_bunker:
        _render_bunker_control(db)

def _render_mission_control(db, img_dir):
    from src.domain.models import ScraperStatusModel, ScraperExecutionLogModel
    st.subheader("📡 Centro de Operaciones")
    
    active_scrapers = db.query(ScraperStatusModel).filter(ScraperStatusModel.status == "running").all()
    
    # Target Selector - Kaizen: Display with Accents but process without them
    import os
    DISPLAY_MAP = {
        "ActionToys": "ActionToys",
        "Fantasia Personajes": "Fantasía Personajes",
        "Frikiverso": "Frikiverso",
        "Pixelatoy": "Pixelatoy",
        "Electropolis": "Electropolis"
    }
    REVERSE_MAP = {v: k for k, v in DISPLAY_MAP.items()}

    selected_shops_disp = st.multiselect(
        "Objetivos de Escaneo",
        options=list(DISPLAY_MAP.values()),
        default=[],
        placeholder="Todos los objetivos (Por defecto)",
        disabled=bool(active_scrapers)
    )
    selected_shops = [REVERSE_MAP[s] for s in selected_shops_disp]
    
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

def _render_bastion_history(db: Session):
    from src.domain.models import OfferHistoryModel
    st.subheader("🛡️ Bastión de Datos: Historial de Movimientos")
    st.caption("Registro imborrable de todas las ofertas que han pasado por el Oráculo.")
    
    limit = st.slider("Ver últimos X movimientos", 10, 200, 50, key="hist_limit")
    
    history = db.query(OfferHistoryModel).order_by(OfferHistoryModel.timestamp.desc()).limit(limit).all()
    
    if not history:
        st.info("El Bastión aún no tiene registros. ¡Empieza a scrapear para generar historia!")
        return
        
    for h in history:
        with st.container(border=True):
            c1, c2 = st.columns([1, 4])
            with c1:
                icon = "🔗" if "LINKED" in h.action_type else ("🌪️" if "PURGED" in h.action_type else "⏳")
                st.markdown(f"### {icon}")
            with c2:
                st.markdown(f"**{h.product_name}**")
                st.caption(f"{h.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {h.shop_name} | {h.action_type}")
                if h.details:
                    st.info(h.details)
                st.code(h.offer_url, language="text")

def _render_purgatory_content(db):
    from src.domain.models import ProductModel, OfferModel, PendingMatchModel, BlackcludedItemModel
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

    # --- UNDO LAST ACTION (PHASE 19) ---
    from src.domain.models import OfferHistoryModel, OfferModel
    last_action = db.query(OfferHistoryModel).filter(OfferHistoryModel.action_type == "LINKED_MANUAL").order_by(OfferHistoryModel.timestamp.desc()).first()
    
    if last_action:
        if st.button(f"⏪ Deshacer: Desvincular '{last_action.product_name}'", use_container_width=True):
            try:
                # 1. Fetch the actual Offer to trigger cascades (PriceHistory)
                offer_to_remove = db.query(OfferModel).filter(OfferModel.url == last_action.offer_url).first()
                if offer_to_remove:
                    db.delete(offer_to_remove)
                
                # 2. Re-create PendingMatch (Atomic with the delete)
                import json
                meta = {}
                try: meta = json.loads(last_action.details) if last_action.details else {}
                except: pass
                
                undone_item = PendingMatchModel(
                    scraped_name=last_action.product_name,
                    shop_name=last_action.shop_name,
                    price=last_action.price,
                    url=last_action.offer_url,
                    currency=meta.get("currency", "EUR"),
                    image_url=meta.get("image_url"),
                    ean=meta.get("ean")
                )
                db.add(undone_item)
                
                # 3. Mark action as undone
                last_action.action_type = "LINKED_MANUAL_UNDONE"
                db.commit()
                st.toast("⏪ Acción revertida. El ítem ha vuelto al Purgatorio.")
                # Clear suggestions cache to force re-calculation if needed
                if "purgatory_suggestions" in st.session_state:
                    st.session_state.purgatory_suggestions.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error al deshacer: {e}")
                db.rollback()

    st.divider()

    # --- CACHE DE SUGERENCIAS (PHASE 19: Performance) ---
    if "purgatory_suggestions" not in st.session_state:
        st.session_state.purgatory_suggestions = {}

    @st.fragment
    def render_purgatory_item(item, all_products, matcher):
        # Usar caché si existe para este item
        if item.id in st.session_state.purgatory_suggestions:
            best_match, best_score = st.session_state.purgatory_suggestions[item.id]
            # Verificar si el producto aún existe en el catálogo actual
            if best_match and best_match not in all_products:
                 best_match = None # Reset if catálogo changed
        else:
            best_match = None
            best_score = 0.0
            for p in all_products:
                _, score, _ = matcher.match(p.name, item.scraped_name, item.url, db_ean=p.ean, scraped_ean=item.ean)
                if score > best_score:
                    best_score = score
                    best_match = p
            st.session_state.purgatory_suggestions[item.id] = (best_match, best_score)

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
                    # Optimized Thumbnails: Using CSS to limit height and avoid layout shift
                    st.markdown(f'<img src="{item.image_url}" style="height:150px; border-radius:10px; margin-bottom:10px; object-fit: contain;">', unsafe_allow_html=True)
                
                if best_match:
                    confidence_color = "green" if best_score > 0.9 else ("orange" if best_score > 0.7 else "gray")
                    st.markdown(f"""
                        <div style="border: 1px solid {confidence_color}; border-left: 5px solid {confidence_color}; padding: 10px; border-radius: 5px; background-color: rgba(0,0,0,0.05); margin-bottom: 10px;">
                            <span style="color: {confidence_color}; font-weight: bold;">🎯 Sugerencia del Oráculo:</span> {best_match.name} 
                            <br><small>Nivel de Confianza: {best_score:.2%}</small>
                        </div>
                    """, unsafe_allow_html=True)
                
                from src.web.shared import render_external_link
                render_external_link(item.url, "Abrir Enlace", key_suffix=f"purg_{item.id}")
                
                c1, c2, c3 = st.columns([2, 1, 1])
                
                # Robust selection logic
                idx_suggestion = 0
                if best_match:
                    try:
                        # Find the index by ID to avoid reference issues
                        for i, p in enumerate(all_products):
                            if p.id == best_match.id:
                                idx_suggestion = i
                                break
                    except Exception: pass

                target_p = c1.selectbox("Vincular a:", all_products, index=idx_suggestion, format_func=lambda x: f"{'✨ ' if best_match and x.id == best_match.id else ''}{x.name}", key=f"purg_sel_{item.id}", help="El Oráculo ha pre-seleccionado la opción más probable.")
                
                if c2.button("✅ Vincular", key=f"purg_ok_{item.id}", type="primary"):
                    if target_p:
                        # RE-FETCH in a local session inside fragment? No, better use a tool or helper.
                        # For now, we'll use a direct DB action.
                        from src.infrastructure.database import SessionLocal
                        with SessionLocal() as local_db:
                            from src.infrastructure.repositories.product import ProductRepository
                            local_repo = ProductRepository(local_db)
                            fresh_p = local_db.query(ProductModel).filter(ProductModel.id == target_p.id).first()
                            fresh_item = local_db.query(PendingMatchModel).filter(PendingMatchModel.id == item.id).first()
                            
                            if fresh_p and fresh_item:
                                local_repo.add_offer(fresh_p, {
                                    "shop_name": fresh_item.shop_name,
                                    "price": fresh_item.price,
                                    "currency": fresh_item.currency,
                                    "url": fresh_item.url,
                                    "is_available": True,
                                    "ean": fresh_item.ean
                                })
                                # LOG HISTORY
                                try:
                                    import json
                                    from src.domain.models import OfferHistoryModel
                                    metadata = {"currency": fresh_item.currency, "image_url": fresh_item.image_url, "ean": fresh_item.ean}
                                    history = OfferHistoryModel(
                                        offer_url=fresh_item.url,
                                        product_name=fresh_item.scraped_name,
                                        shop_name=fresh_item.shop_name,
                                        price=fresh_item.price,
                                        action_type="LINKED_MANUAL",
                                        details=json.dumps(metadata)
                                    )
                                    local_db.add(history)
                                except: pass
                                
                                local_db.delete(fresh_item)
                                local_db.commit()
                                st.toast("Vinculado con éxito.")
                                st.rerun()
                
                if c3.button("🔥 Descartar", key=f"purg_del_{item.id}"):
                     from src.infrastructure.database import SessionLocal
                     with SessionLocal() as local_db:
                        fresh_item = local_db.query(PendingMatchModel).filter(PendingMatchModel.id == item.id).first()
                        if fresh_item:
                            bl = BlackcludedItemModel(url=fresh_item.url, scraped_name=fresh_item.scraped_name, reason="purgatory_discard")
                            local_db.add(bl)
                            local_db.delete(fresh_item)
                            local_db.commit()
                            st.toast("Descartado.")
                            st.rerun()

    # Render items
    for item in pending_items:
        render_purgatory_item(item, all_products, matcher)

def _render_bunker_control(db):
    """
    UI for managing backups and snapshots.
    """
    from pathlib import Path
    import os
    from datetime import datetime
    
    st.subheader("🛡️ La Cámara de Grayskull: Salvaguarda de Eternia")
    st.info("Aquí residen los snapshots crudos de los scrapers y los sellos (backups) de la base de datos.")
    
    col1, col2 = st.columns(2)
    
    # 1. Database Vaults
    with col1:
        st.markdown("### 🏰 Bóvedas del Oráculo (Backups DB)")
        vault_path = Path("backups/database")
        if vault_path.exists():
            vaults = sorted(list(vault_path.glob("*.json")), key=os.path.getmtime, reverse=True)
            if vaults:
                for idx, v in enumerate(vaults[:5]): # Show last 5
                    mtime = datetime.fromtimestamp(v.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    size = v.stat().st_size / 1024
                    
                    c1_v, c2_v = st.columns([3, 1])
                    c1_v.write(f"**{v.name}**\n\n({mtime}) - {size:.1f} KB")
                    
                    if c2_v.button("♻️", key=f"restore_v_{idx}", help="Restaurar este sello"):
                        st.session_state[f"confirm_restore_{idx}"] = True
                    
                    if st.session_state.get(f"confirm_restore_{idx}"):
                        st.warning(f"⚠️ **¡ADVERTENCIA DE ETERNIA!**\n\nEsto ELIMINARÁ todos los datos actuales y restaurará el sello: {v.name}")
                        if st.button("SÍ, RESTAURAR AHORA", key=f"do_restore_{idx}", type="primary"):
                            from src.jobs.restore_vault import restore_from_vault
                            with st.spinner("Reconstruyendo Eternia..."):
                                restore_from_vault(str(v))
                                st.success("✅ Oráculo Restaurado.")
                                del st.session_state[f"confirm_restore_{idx}"]
                                st.rerun()
                        if st.button("Abortar", key=f"cancel_restore_{idx}"):
                            del st.session_state[f"confirm_restore_{idx}"]
                            st.rerun()
                
                st.caption("Los sellos permiten volver a un estado previo en segundos.")
            else:
                st.write("No hay bóvedas selladas aún.")
        else:
            st.write("Cámara no inicializada.")

    # 2. Raw Snapshots
    with col2:
        st.markdown("### 💾 Caja Negra (Snapshots Scrapers)")
        snap_path = Path("backups/raw_snapshots")
        if snap_path.exists():
            snaps = sorted(list(snap_path.glob("*.json")), key=os.path.getmtime, reverse=True)
            if snaps:
                for s in snaps[:5]:
                    mtime = datetime.fromtimestamp(s.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    st.write(f"- {s.name} ({mtime})")
                
                st.write(f"Total: {len(snaps)} snapshots guardados.")
            else:
                st.write("No hay snapshots crudos.")
        else:
            st.write("Caja negra no inicializada.")
    
    st.markdown("---")
    if st.button("🛡️ Sellar Bóveda Ahora (Manual Backup)"):
        from src.core.backup_manager import BackupManager
        bm = BackupManager()
        path = bm.create_database_backup(db)
        if path:
            st.success(f"Bóveda sellada con éxito: {Path(path).name}")
            st.rerun()

    with st.expander("📖 Protocolo de Grayskull (Manual de Recuperación)"):
        st.markdown("""
        ### 🧪 Procedimiento de Emergencia y Salvaguarda Total
        Este panel es la **Llave Maestra** para revertir el estado del Oráculo si ocurre un desastre.
        
        **📍 ¿A dónde van los datos?**
        La restauración es un "Efecto Espejo". El sistema toma el sello JSON y sobrescribe la base de datos que esté activa en ese momento (**Supabase** si estás en la nube, **SQLite** si estás en local). No necesitas configurar nada adicional; el Oráculo sabe dónde vive su poder.

        **⚙️ ¿Qué es automático y qué no?**
        - **Auto-Protección (Activa):** El sistema ya tiene un *Circuit Breaker* que frena actualizaciones locas y un *Query Shield* que evita errores de esquema. Si algo falla durante el día, el robot intentará auto-corregirse solo.
        - **Restauración (Manual por Seguridad):** La vuelta al pasado (Time Machine) es manual para evitar que el sistema borre datos nuevos por error al intentar "ayudarte" tras un fallo de red. Tú tienes el control final.

        **1. Selección del Sello:**
        - El sello más reciente es el punto de retorno estándar.
        
        **2. Restauración (Botón ♻️):**
        - Se borrará TODO el catálogo actual para ser reemplazado por la copia. 
        - **Acción Post-Rescate:** Ninguna. Solo recarga la pestaña del navegador para ver tu catálogo restaurado.
        
        **3. Sellado Manual:**
        - Usa **Sellar Bóveda Ahora** antes de hacer limpiezas masivas en el Purgatorio.
        
        **4. Último Recurso (Terminal):**
        - Si la web cae: `python src/jobs/restore_vault.py`
        """)
