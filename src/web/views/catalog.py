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
        st.image(str(img_dir / "Catalogo.png"), width="stretch")
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

    
    # --- Performance Cache ---
    @st.cache_data(ttl=300) # Cache for 5 minutes
    def get_catalog_products(_db_session, _search, _cat, _filter_mode, _current_uid, _sort_opt): 
        # Note: _db_session is underscored to prevent hashing (it's not pickle-safe), but we need a fresh session inside if caching.
        # Actually, for st.cache_data, we should return Pydantic models or plain dicts, not ORM objects attached to session.
        # However, eager loading (joinedload) can work if we detach them.
        
        # Re-create session inside cache to avoid Thread errors with Streamlit
        from src.infrastructure.database import SessionLocal
        with SessionLocal() as session:
            q = session.query(ProductModel)
            
            # Apply filters
            if _search:
                q = q.filter(ProductModel.name.ilike(f"%{_search}%"))
            if _cat != "Todas":
                q = q.filter(ProductModel.category == _cat)
                
            if _filter_mode == "Adquiridos":
                q = q.join(CollectionItemModel).filter(CollectionItemModel.owner_id == _current_uid)
            elif _filter_mode == "Faltantes":
                subq = session.query(CollectionItemModel.product_id).filter(CollectionItemModel.owner_id == _current_uid)
                q = q.filter(~ProductModel.id.in_(subq))
            
            # Eager load offers for price sorting/display to avoid N+1 queries later
            from sqlalchemy.orm import joinedload
            q = q.options(joinedload(ProductModel.offers))
            
            results = q.all()
            
            # Sort in Python (since we need computed price logic not easy in SQL for this schema)
            if _sort_opt == "Nombre (A-Z)":
                results.sort(key=lambda x: x.name.lower())
            elif _sort_opt == "Nombre (Z-A)":
                results.sort(key=lambda x: x.name.lower(), reverse=True)
            elif "Precio" in _sort_opt:
                def get_price(p):
                    if not p.offers: return 999999.0
                    valid = [o.price for o in p.offers if o.price > 0]
                    return min(valid) if valid else 999999.0
                results.sort(key=get_price, reverse="Mayor" in _sort_opt)
                
            # Serialize to prevent session detach issues
            # We return a list of detached instances or a specialized DTO if needed. 
            # SQLAlchemy objs can be cached if they are fully loaded and we use expunge_all.
            session.expunge_all()
            return results

    # Execute Cached Query
    # We pass 'str(db.bind.url)' as a hash key if we wanted to invalidate on DB change, but TTL is fine.
    # We pass user.id (int) not the object to be safe.
    products = get_catalog_products(None, search, sel_cat, filter_opt, current_user_id, sort_opt)

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

    # Optimized Ownership Check with Optimistic UI
    # 1. Fetch DB Truth
    owned_ids_query = db.query(CollectionItemModel.product_id).filter(CollectionItemModel.owner_id == current_user_id).all()
    owned_ids_set = {r[0] for r in owned_ids_query}
    
    # 2. Initialize Optimistic State Override if not exists
    if "optimistic_updates" not in st.session_state:
        st.session_state.optimistic_updates = {}

    # --- Render List ---
    for p in visible_products:
        # Determine Status: DB Truth + Local Overrides
        is_owned_db = p.id in owned_ids_set
        
        # Apply override if exists for this product
        if p.id in st.session_state.optimistic_updates:
            is_owned = st.session_state.optimistic_updates[p.id]
        else:
            is_owned = is_owned_db
            
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
                if st.button(btn_label, key=f"btn_{p.id}", width="stretch"):
                    # Optimistic Update: Set the OPPOSITE of what is currently displayed
                    st.session_state.optimistic_updates[p.id] = not is_owned
                    
                    if toggle_ownership(db, p.id, current_user_id):
                        st.cache_data.clear() # Force refresh data
                        st.rerun()
            
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
