import streamlit as st
from src.infrastructure.database import SessionLocal
from src.domain.models import ProductModel, CollectionItemModel

def toggle_ownership(db, product_id: int, user_id: int):
    """
    Toggles the ownership status of a product for the given user.
    """
    try:
        product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
        
        if product:
            existing_item = db.query(CollectionItemModel).filter_by(
                product_id=product.id,
                owner_id=user_id
            ).first()

            if existing_item:
                db.delete(existing_item)
                st.toast(f"🗑️ {product.name} eliminado de tu colección")
            else:
                item = CollectionItemModel(
                    product_id=product.id, 
                    acquired=True,
                    owner_id=user_id
                )
                db.add(item)
                st.toast(f"✅ {product.name} añadido a tu colección")
            
            db.commit()
            return True
            
    except Exception as e:
        db.rollback()
        st.error(f"Error actualizando colección: {e}")
        return False

def render_external_link(url: str, text: str = "Ver Oferta", key_suffix: str = ""):
    """
    Renders a safe external link using native Streamlit components.
    """
    # Use native link_button which handles external links securely and reliably
    st.link_button(f"🔗 {text}", url, use_container_width=True)
