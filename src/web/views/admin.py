import streamlit as st
from sqlalchemy.orm import Session
from src.domain.models import ProductModel, OfferModel, PendingMatchModel, BlackcludedItemModel, CollectionItemModel

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
    c1, c2 = st.columns([1, 8])
    with c1:
        st.image(str(img_dir / "Purgatorio.png"), use_container_width=True)
    with c2:
        st.markdown("# Purgatorio (Conexión Manual)")
    
    st.info("Aquí yacen las ofertas que no encontraron su camino...")
    
    # --- Pagination Logic ---
    PAGE_SIZE = 50
    if "purgatory_page" not in st.session_state:
        st.session_state.purgatory_page = 0

    total_items = db.query(PendingMatchModel).count()
    if total_items == 0:
        st.success("El Purgatorio está vacío. ¡Alabado sea!")
        return

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

    # Group controls
    for item in pending_items:
        with st.expander(f"{item.scraped_name} - {item.shop_name} ({item.price}€)", expanded=True):
            if item.image_url:
                st.image(item.image_url, width=100)
            # st.code(item.url)
            from src.web.shared import render_external_link
            render_external_link(item.url, "Abrir Enlace", key_suffix=f"purg_{item.id}")
            
            c1, c2, c3 = st.columns([2, 1, 1])
            
            # Match
            from src.infrastructure.repositories.product import ProductRepository
            repo = ProductRepository(db) # We need repo for searching? Or just DB query.
            # Simple match by name logic?
            # User types ID or selects product.
            
            # Simple Selection
            all_products = db.query(ProductModel).order_by(ProductModel.name).all()
            target_p = c1.selectbox("Vincular a:", all_products, format_func=lambda x: x.name, key=f"purg_sel_{item.id}")
            
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
