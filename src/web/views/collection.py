import streamlit as st
from sqlalchemy.orm import Session
from src.domain.models import ProductModel, CollectionItemModel
from src.web.shared import toggle_ownership

def render(db: Session, img_dir, user):
    c1, c2 = st.columns([1, 8])
    with c1:
         st.image(str(img_dir / "Mi_Coleccion.png"), width="stretch")
    with c2:
        st.markdown("# Mi Fortaleza (Colección)")
    
    current_user_id = user.id
    
    # --- Controls ---
    col_sort, _ = st.columns([1, 1])
    with col_sort:
        sort_mode = st.radio(
            "Ordenar por:", 
            ["Fecha de Adquisición (Nuevos primero)", "Alfabético (A-Z)"],
            label_visibility="collapsed",
            horizontal=True
        )

    
    # --- Performance Cache ---
    @st.cache_data(ttl=300)
    def get_user_collection(_user_id, _sort_mode):
        from src.infrastructure.database import SessionLocal
        with SessionLocal() as session:
            q = (
                session.query(ProductModel, CollectionItemModel.acquired_at)
                .join(CollectionItemModel)
                .filter(CollectionItemModel.owner_id == _user_id)
            )
            
            if "Fecha" in _sort_mode:
                q = q.order_by(CollectionItemModel.acquired_at.desc())
            else:
                q = q.order_by(ProductModel.name)
            
            results = q.all()
            session.expunge_all() # Detach
            return results

    # Optimize: Only fetch from DB if not optimistically modified
    # Actually we fetch base truth then patch it.
    owned_db_rows = get_user_collection(current_user_id, sort_mode)
    
    # Apply Optimistic Updates
    if "optimistic_updates" not in st.session_state:
        st.session_state.optimistic_updates = {}
        
    owned = []
    # 1. Process DB items (Filter deletions)
    for p, acquired_at in owned_db_rows:
        if st.session_state.optimistic_updates.get(p.id) is False:
            continue
        # Attach timestamp for later sorting
        p.temp_acquired_at = acquired_at 
        owned.append(p)
        
    # 2. Process Optimistic Additions
    # We attribute "now" as time for optimistic adds
    from datetime import datetime
    owned_ids = {p.id for p in owned}
    added_ids = [pid for pid, status in st.session_state.optimistic_updates.items() if status is True and pid not in owned_ids]
    
    if added_ids:
        new_products = db.query(ProductModel).filter(ProductModel.id.in_(added_ids)).all()
        for np in new_products:
            np.temp_acquired_at = datetime.utcnow() # Assume 'now'
            owned.append(np)
            
    # 3. Final Sort (Merge DB + Optimistic)
    if "Fecha" in sort_mode:
        owned.sort(key=lambda x: x.temp_acquired_at or datetime.min, reverse=True)
    else:
        owned.sort(key=lambda x: x.name)
    
    if not owned:
        st.warning("Tu fortaleza está vacía. Ve al **Catálogo** y añade tus figuras.")
        return

    st.success(f"Tienes {len(owned)} reliquias en tu poder.")
    
    # Grid View: 2 columns for Mobile
    cols = st.columns(2)
    for idx, p in enumerate(owned):
        with cols[idx % 2]:
            st.markdown(f"**{p.name}**") 
            if p.image_url:
                st.image(p.image_url, width="stretch")
            
            if st.button("❌ Eliminar", key=f"del_col_{p.id}", width="stretch"):
                # Optimistic Update
                st.session_state.optimistic_updates[p.id] = False
                
                if toggle_ownership(db, p.id, current_user_id):
                    st.cache_data.clear() # Force refresh
                    st.rerun()
