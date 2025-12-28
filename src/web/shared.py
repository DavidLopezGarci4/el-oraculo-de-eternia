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

def render_external_link(url: str, shop_name: str = None, price: float = None, text: str = "Ver Oferta", key_suffix: str = ""):
    """
    Renders an enriched external link button.
    Format: [Shop Name] - [Price]€
    """
    if shop_name and price is not None:
        button_text = f"{shop_name} - {price:.2f}€"
    else:
        button_text = text
        
    st.link_button(f"🔗 {button_text}", url, use_container_width=True)

def normalize_shop_name(name: str, mode: str = "technical") -> str:
    """
    Normalizes shop names to avoid duplicates due to accents/variants.
    'technical': Fantasia Personajes (for DB)
    'visual': Fantasía Personajes (for UI)
    """
    if not name: return name
    
    fantasia_variants = ["Fantasia", "Fantasia Personajes", "Fantasía Personajes"]
    if name in fantasia_variants:
        return "Fantasia Personajes" if mode == "technical" else "Fantasía Personajes"
        
    return name
