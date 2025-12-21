import streamlit as st
from sqlalchemy.orm import Session
from src.domain.models import ProductModel, CollectionItemModel
from src.web.shared import toggle_ownership

def render(db: Session, img_dir, user):
    c1, c2 = st.columns([1, 8])
    with c1:
         st.image(str(img_dir / "Mi_Coleccion.png"), use_container_width=True)
    with c2:
        st.markdown("# Mi Fortaleza (Colección)")
    
    current_user_id = user.id
    
    # Query owned products
    owned = (
        db.query(ProductModel)
        .join(CollectionItemModel)
        .filter(CollectionItemModel.owner_id == current_user_id)
        .all()
    )
    
    if not owned:
        st.warning("Tu fortaleza está vacía. Ve al **Catálogo** y añade tus figuras.")
        return

    st.success(f"Tienes {len(owned)} reliquias en tu poder.")
    
    # Grid View
    cols = st.columns(4)
    for idx, p in enumerate(owned):
        with cols[idx % 4]:
            if p.image_url:
                st.image(p.image_url, use_container_width=True)
            st.caption(p.name)
            if st.button("❌", key=f"del_col_{p.id}"):
                toggle_ownership(db, p.id, current_user_id)
                st.rerun()
