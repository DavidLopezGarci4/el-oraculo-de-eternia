import streamlit as st
import math
from sqlalchemy.orm import Session
from src.web.shared import toggle_ownership
from src.web.views.admin import render_inline_product_admin
from src.infrastructure.repositories.product import ProductRepository

def render(db: Session, img_dir, user, repo: ProductRepository):
    from src.domain.models import ProductModel, CollectionItemModel, OfferModel, PriceHistoryModel, PriceAlertModel
    total_products = db.query(ProductModel).count()
    # Header
    c1, c2 = st.columns([1, 8])
    with c1:
        st.image(str(img_dir / "Catalogo.png"), width="stretch")
    with c2:
        st.markdown("# Catálogo de Eternia")
    st.caption(f"Explorando {total_products} reliquias en el multiverso...")
    
    current_user_id = user.id

    # --- Filters ---
    with st.expander("🔍 Buscador, Filtros y Orden", expanded=True):
        col_search, col_cat, col_page_jump = st.columns([2, 1, 1])
        with col_search:
            search = st.text_input("Buscador", placeholder="Nombre de la figura...", label_visibility="collapsed", key="catalog_search_input")
        with col_cat:
            cats = [r[0] for r in db.query(ProductModel.category).distinct() if r[0]]
            sel_cat = st.selectbox("Categoría", ["Todas"] + sorted(cats), label_visibility="collapsed")
        with col_page_jump:
            # Placeholder for page jump - total_pages needed
            page_jump_placeholder = st.empty()

        col_filter, col_sort = st.columns(2)
        with col_filter:
            filter_opt = st.selectbox("Estado", ["Todos", "Adquiridos", "Faltantes"])
        with col_sort:
            sort_opt = st.selectbox("Orden", ["Nombre (A-Z)", "Nombre (Z-A)", "Precio (Menor a Mayor)", "Precio (Mayor a Menor)"])

    
    # --- Performance Cache: Master Data Load ---
    @st.cache_data(ttl=300) # 5m cache
    def get_master_catalog_df(_current_uid):
        from src.infrastructure.database import SessionLocal
        import pandas as pd
        with SessionLocal() as session:
            # Eager load offers and price history for total performance
            from sqlalchemy.orm import joinedload
            products_raw = session.query(ProductModel).options(
                joinedload(ProductModel.offers).joinedload(OfferModel.price_history)
            ).all()
            owned_ids = {r[0] for r in session.query(CollectionItemModel.product_id).filter(CollectionItemModel.owner_id == _current_uid).all()}
            
            data = []
            for p in products_raw:
                prices = [o.price for o in p.offers if o.price > 0]
                min_prices = [o.min_price for o in p.offers if o.min_price > 0]
                
                # Serialize offers for the UI (Avoiding DetachedInstanceError)
                serialized_offers = []
                serialized_history = []
                for o in p.offers:
                    serialized_offers.append({
                        "id": o.id,
                        "shop_name": o.shop_name,
                        "price": o.price,
                        "url": o.url
                    })
                    for ph in o.price_history:
                        serialized_history.append({
                            "Fecha": ph.recorded_at,
                            "Precio": ph.price,
                            "Tienda": o.shop_name
                        })
                
                data.append({
                    "id": p.id,
                    "name": p.name,
                    "category": p.category or "MOTU",
                    "image_url": p.image_url,
                    "is_owned": p.id in owned_ids,
                    "best_price": min(prices) if prices else 999999.0,
                    "historic_low": min(min_prices) if min_prices else 999999.0,
                    "offers": serialized_offers,
                    "history": serialized_history
                })
            return pd.DataFrame(data)

    # 1. Load Data
    df = get_master_catalog_df(current_user_id)
    
    # 2. Apply Filters (Instant in memory)
    filtered_df = df.copy()
    if search:
        filtered_df = filtered_df[filtered_df['name'].str.contains(search, case=False, na=False)]
    if sel_cat != "Todas":
        filtered_df = filtered_df[filtered_df['category'] == sel_cat]
        
    if filter_opt == "Adquiridos":
        filtered_df = filtered_df[filtered_df['is_owned'] == True]
    elif filter_opt == "Faltantes":
        filtered_df = filtered_df[filtered_df['is_owned'] == False]
        
    # 3. Sort (Instant in memory)
    if sort_opt == "Nombre (A-Z)":
        filtered_df = filtered_df.sort_values("name")
    elif sort_opt == "Nombre (Z-A)":
        filtered_df = filtered_df.sort_values("name", ascending=False)
    elif "Precio" in sort_opt:
        filtered_df = filtered_df.sort_values("best_price", ascending="Menor" in sort_opt)

    # --- Pagination ---
    PAGE_SIZE = 50
    total_items = len(filtered_df)
    total_pages = max(1, math.ceil(total_items / PAGE_SIZE))
    
    if "catalog_page" not in st.session_state:
        st.session_state.catalog_page = 0
    
    # Boundary check for pagination
    st.session_state.catalog_page = min(st.session_state.catalog_page, total_pages - 1)
    st.session_state.catalog_page = max(0, st.session_state.catalog_page)

    # Update Page Jump Selector in the filters area
    with page_jump_placeholder:
        jump_page = st.number_input("Página", min_value=1, max_value=total_pages, value=st.session_state.catalog_page + 1, label_visibility="collapsed")
        if jump_page - 1 != st.session_state.catalog_page:
            st.session_state.catalog_page = jump_page - 1
            st.rerun()

    start_idx = st.session_state.catalog_page * PAGE_SIZE
    visible_df = filtered_df.iloc[start_idx : start_idx + PAGE_SIZE]
    
    st.divider()
    st.caption(f"Encontradas {total_items} figuras. Página {st.session_state.catalog_page+1} de {total_pages}")

    # Use a set for ownership truth from the DataFrame for fast lookup in render loop
    if "optimistic_updates" not in st.session_state:
        st.session_state.optimistic_updates = {}
    
    # --- Render List ---
    for _, row in visible_df.iterrows():
        p_id = row['id']
        p_name = row['name']
        p_cat = row['category']
        p_img = row['image_url']
        p_best = row['best_price']
        p_hist = row['historic_low']
        p_is_owned = row['is_owned']
        p_offers = row['offers']
        p_history = row['history']
        
        is_owned = st.session_state.optimistic_updates.get(p_id, p_is_owned)
        btn_label = "✅ En Colección" if is_owned else "➕ Añadir"
        current_best = f"{p_best:.2f}€" if p_best < 900000 else "---"
        historic_low = f"{p_hist:.2f}€" if p_hist < 900000 else "---"

        with st.container():
            c_img, c_info, c_price_curr, c_price_hist, c_action = st.columns([1, 3, 1.5, 1.5, 1.5])
            
            with c_img:
                if p_img:
                    st.image(p_img, width=80)
                else:
                    st.write("🖼️")
            
            with c_info:
                if user.role == "admin":
                    p_obj_live = db.get(ProductModel, p_id)
                    render_inline_product_admin(db, p_obj_live, current_user_id)
                else:
                    st.subheader(p_name)
                    st.caption(f"Categoría: {p_cat}")
                
                # Offers Expander
                if p_offers:
                     with st.expander(f"Ver {len(p_offers)} tiendas y Precios 📉"):
                          for o in p_offers:
                               from src.web.shared import render_external_link
                               render_external_link(o['url'], "Ver Oferta", key_suffix=f"cat_{o['id']}")
                          
                          # Chart Logic
                          st.divider()
                          st.subheader("Evolución Temporal")
                          if p_history:
                               try:
                                   import pandas as pd
                                   df_hist = pd.DataFrame(p_history).sort_values("Fecha")
                                   st.line_chart(df_hist, x="Fecha", y="Precio", color="Tienda")
                               except Exception:
                                   pass
                          else:
                               st.info("Faltan datos históricos.")

            with c_price_curr:
                st.metric("Mejor Precio", current_best)
            
            with c_price_hist:
                st.metric("Mín. Histórico", historic_low)
            
            with c_action:
                if st.button(btn_label, key=f"btn_{p_id}", width="stretch"):
                    st.session_state.optimistic_updates[p_id] = not is_owned
                    if toggle_ownership(db, p_id, current_user_id):
                        st.cache_data.clear() # Cache invalidation on change
                        st.rerun()
                
                # Botón de Alerta Centinela (Añadido Fase 15)
                with st.popover("🔔 Alerta", use_container_width=True):
                    st.write(f"Vigilar {p_name}")
                    t_price = st.number_input("Avisar si baja de (€)", min_value=1.0, value=max(1.0, p_best * 0.9 if p_best < 900000 else 20.0), key=f"alrt_in_{p_id}")
                    if st.button("Activar Centinela", key=f"alrt_btn_{p_id}", type="primary"):
                        # Lógica rápida de inserción
                        exists = db.query(PriceAlertModel).filter(PriceAlertModel.user_id == user.id, PriceAlertModel.product_id == p_id).first()
                        if not exists:
                            new_al = PriceAlertModel(user_id=user.id, product_id=p_id, target_price=t_price)
                            db.add(new_al)
                            db.commit()
                            st.success("¡Centinela desplegado!")
                        else:
                            st.warning("Ya tienes una alerta activa.")
            
            st.markdown("---")

    # --- Footer Navigation ---
    c_prev, c_page, c_next = st.columns([1, 2, 1])
    
    with c_prev:
        if st.session_state.catalog_page > 0:
            if st.button("⬅️ Anterior", width="stretch"):
                st.session_state.catalog_page -= 1
                st.rerun()
                
    with c_page:
        st.markdown(f"<div style='text-align: center'>Página {st.session_state.catalog_page + 1} de {total_pages}</div>", unsafe_allow_html=True)
        
    with c_next:
        if st.session_state.catalog_page < total_pages - 1:
            if st.button("Siguiente ➡️", width="stretch"):
                st.session_state.catalog_page += 1
                st.rerun()
