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
    
    # Query owned products
    owned_db = (
        db.query(ProductModel)
        .join(CollectionItemModel)
        .filter(CollectionItemModel.owner_id == current_user_id)
        .all()
    )
    
    # Apply Optimistic Updates
    if "optimistic_updates" not in st.session_state:
        st.session_state.optimistic_updates = {}
        
    owned = []
    for p in owned_db:
        # If explicitly set to False in optimistic state, skip it (virtual delete)
        if st.session_state.optimistic_updates.get(p.id) is False:
            continue
        owned.append(p)
    
    # Also include items optimistically added (if we want to show them immediately in collection view)
    # However, 'owned_db' is a list of ProductModels. To show new ones, we'd need to fetch them.
    # For now, let's focus on instant DELETE as that's the primary interaction here.
    
    if not owned:
        st.warning("Tu fortaleza está vacía. Ve al **Catálogo** y añade tus figuras.")
        return

    st.success(f"Tienes {len(owned)} reliquias en tu poder.")
    
    # Grid View
    cols = st.columns(4)
    for idx, p in enumerate(owned):
        with cols[idx % 4]:
            if p.image_url:
                st.image(p.image_url, width="stretch")
            st.caption(p.name)
            if st.button("❌", key=f"del_col_{p.id}"):
                # Optimistic Update: Mark as removed immediately
                st.session_state.optimistic_updates[p.id] = False
                
                if toggle_ownership(db, p.id, current_user_id):
                    st.rerun()
