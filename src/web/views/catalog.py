import streamlit as st
import math
from sqlalchemy.orm import Session
from src.domain.models import ProductModel, CollectionItemModel
from src.web.shared import toggle_ownership
from src.web.views.admin import render_inline_product_admin
from src.infrastructure.repositories.product import ProductRepository

def render(db: Session, img_dir, user, repo: ProductRepository):
    total_products = db.query(ProductModel).count()
    # Header
    c1, c2 = st.columns([1, 8])
    with c1:
        st.image(str(img_dir / "Catalogo.png"), use_container_width=True)
    with c2:
        st.markdown("# Catálogo de Eternia")
    st.caption(f"Explorando {total_products} reliquias en el multiverso...")
    
    current_user_id = user.id

    # --- Filters ---
    with st.expander("🔍 Buscador, Filtros y Orden", expanded=True):
        col_search, col_cat = st.columns([2, 1])
        with col_search:
            search = st.text_input("Buscador", placeholder="Nombre de la figura...", label_visibility="collapsed")
        with col_cat:
            cats = [r[0] for r in db.query(ProductModel.category).distinct() if r[0]]
            sel_cat = st.selectbox("Categoría", ["Todas"] + sorted(cats), label_visibility="collapsed")

        col_filter, col_sort = st.columns(2)
        with col_filter:
            filter_opt = st.selectbox("Estado", ["Todos", "Adquiridos", "Faltantes"])
        with col_sort:
            sort_opt = st.selectbox("Orden", ["Nombre (A-Z)", "Nombre (Z-A)", "Precio (Menor a Mayor)", "Precio (Mayor a Menor)"])

    # --- Query Building ---
    query = db.query(ProductModel)
    
    if search:
        query = query.filter(ProductModel.name.ilike(f"%{search}%"))
    if sel_cat != "Todas":
        query = query.filter(ProductModel.category == sel_cat)
    if filter_opt == "Adquiridos":
        query = query.join(CollectionItemModel).filter(CollectionItemModel.owner_id == current_user_id)
    elif filter_opt == "Faltantes":
        subq = db.query(CollectionItemModel.product_id).filter(CollectionItemModel.owner_id == current_user_id)
        query = query.filter(~ProductModel.id.in_(subq))
    
    # Exec & Sort (In-Memory for simplicity regarding prices)
    products = query.all()
    
    if sort_opt == "Nombre (A-Z)":
        products.sort(key=lambda x: x.name.lower())
    elif sort_opt == "Nombre (Z-A)":
        products.sort(key=lambda x: x.name.lower(), reverse=True)
    elif "Precio" in sort_opt:
        def get_price(p):
            if not p.offers: return 999999.0
            valid = [o.price for o in p.offers if o.price > 0]
            return min(valid) if valid else 999999.0
        reverse = "Mayor" in sort_opt
        products.sort(key=get_price, reverse=reverse)

    # --- Pagination ---
    PAGE_SIZE = 50
    total_items = len(products)
    total_pages = math.ceil(total_items / PAGE_SIZE)
    
    if "catalog_page" not in st.session_state:
        st.session_state.catalog_page = 0
        
    # Boundary Check
    if st.session_state.catalog_page >= total_pages:
        st.session_state.catalog_page = max(0, total_pages - 1)
        
    start_idx = st.session_state.catalog_page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    
    # Slice
    visible_products = products[start_idx:end_idx]
    
    st.divider()
    st.caption(f"Mostrando {start_idx+1}-{min(end_idx, total_items)} de {total_items} figuras.")

    # --- Render List ---
    for p in visible_products:
        is_owned = any(i.owner_id == current_user_id for i in p.collection_items)
        btn_label = "✅ En Colección" if is_owned else "➕ Añadir"
        
        current_best = "---"
        historic_low = "---"
        if p.offers:
            prices = [o.price for o in p.offers if o.price > 0]
            if prices: current_best = f"{min(prices):.2f}€"
            mins = [o.min_price for o in p.offers if o.min_price > 0]
            if mins: historic_low = f"{min(mins):.2f}€"

        with st.container():
            c_img, c_info, c_price_curr, c_price_hist, c_action = st.columns([1, 3, 1.5, 1.5, 1.5])
            
            with c_img:
                if p.image_url:
                    st.image(p.image_url, width=80)
                else:
                    st.write("🖼️")
            
            with c_info:
                if user.role == "admin":
                    render_inline_product_admin(db, p, current_user_id)
                else:
                    st.subheader(p.name)
                    st.caption(f"Categoría: {p.category}")
                
                # Offers Expander
                if p.offers:
                     with st.expander(f"Ver {len(p.offers)} tiendas y Precios 📉"):
                          for o in p.offers:
                               from src.web.shared import render_external_link
                               render_external_link(o.url, "Ver Oferta", key_suffix=f"cat_{o.id}")
                          
                          # Chart Logic
                          st.divider()
                          st.subheader("Evolución Temporal")
                          try:
                              import pandas as pd
                              chart_data = []
                              for o in p.offers:
                                  for ph in o.price_history:
                                      chart_data.append({
                                          "Fecha": ph.recorded_at,
                                          "Precio": ph.price,
                                          "Tienda": o.shop_name
                                      })
                              if chart_data:
                                  df_hist = pd.DataFrame(chart_data).sort_values("Fecha")
                                  st.line_chart(df_hist, x="Fecha", y="Precio", color="Tienda")
                              else:
                                  st.info("Faltan datos históricos.")
                          except Exception:
                              pass

            with c_price_curr:
                st.metric("Mejor Precio", current_best)
            
            with c_price_hist:
                st.metric("Mín. Histórico", historic_low)
            
            with c_action:
                if st.button(btn_label, key=f"btn_{p.id}", use_container_width=True):
                    toggle_ownership(db, p.id, current_user_id)
                    st.rerun()
            
            st.markdown("---")

    # --- Footer Navigation ---
    c_prev, c_page, c_next = st.columns([1, 2, 1])
    
    with c_prev:
        if st.session_state.catalog_page > 0:
            if st.button("⬅️ Anterior", use_container_width=True):
                st.session_state.catalog_page -= 1
                st.rerun()
                
    with c_page:
        st.markdown(f"<div style='text-align: center'>Página {st.session_state.catalog_page + 1} de {total_pages}</div>", unsafe_allow_html=True)
        
    with c_next:
        if st.session_state.catalog_page < total_pages - 1:
            if st.button("Siguiente ➡️", use_container_width=True):
                st.session_state.catalog_page += 1
                st.rerun()
