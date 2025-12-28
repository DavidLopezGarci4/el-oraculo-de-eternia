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
                
                # Serialize offers for the UI with Deduplication (Active Offer logic)
                # We want the newest offer per shop_name for the actionable links
                serialized_offers = []
                serialized_history = []
                
                # Deduplication logic: Sort by ID desc (proxy for newest) and pick first per shop
                deduped_offers = {}
                sorted_offers = sorted(p.offers, key=lambda x: x.id, reverse=True)
                
                for o in sorted_offers:
                    if o.shop_name not in deduped_offers:
                        deduped_offers[o.shop_name] = {
                            "id": o.id,
                            "shop_name": o.shop_name,
                            "price": o.price,
                            "url": o.url
                        }
                    
                    # Fill history with EVERYTHING (Deduplication MUST NOT affect analytics)
                    for ph in o.price_history:
                        serialized_history.append({
                            "Fecha": ph.recorded_at,
                            "Precio": ph.price,
                            "Tienda": o.shop_name
                        })
                
                serialized_offers = list(deduped_offers.values())
                
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

    # ... (skipping some unchanged filtered_df/pagination logic)
    
    # Render List (around line 175)
    # ...
                # Offers Expander
                if p_offers:
                     with st.expander(f"Ver {len(p_offers)} tiendas y Precios 📉"):
                          for o in p_offers:
                               from src.web.shared import render_external_link
                               # Enriched format: [Shop] - [Price]€
                               render_external_link(o['url'], shop_name=o['shop_name'], price=o['price'], key_suffix=f"cat_{o['id']}")
                          
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
