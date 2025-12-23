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
    except Exception as e:
        db.rollback()
        st.error(f"Error actualizando colección: {e}")

def render_external_link(url: str, text: str = "Ver Oferta", key_suffix: str = ""):
    """
    Renders a safe external link with a fallback copy button.
    Solves issues with embedded browsers blocking navigation.
    """
    # Consolidated Popover (User Requested)
    with st.popover(f"🔗 {text}", width="stretch", help="Elige cómo abrir el enlace"):
        st.write("**Abrir oferta en:**")
        
        c1, c2 = st.columns(2)
        import subprocess
        
        with c1:
            if st.button("🔵 Edge", key=f"open_edge_{key_suffix}_{url[-10:]}", width="stretch"):
                try:
                    subprocess.run(f'start msedge "{url}"', shell=True)
                except Exception as e:
                    st.error(f"Error: {e}")
        
        with c2:
            if st.button("🟢 Chrome", key=f"open_chrome_{key_suffix}_{url[-10:]}", width="stretch"):
                try:
                    subprocess.run(f'start chrome "{url}"', shell=True)
                except Exception as e:
                    st.error(f"Error: {e}")
        
        if st.button("🌐 Predeterminado", key=f"open_def_{key_suffix}_{url[-10:]}", width="stretch"):
             import webbrowser
             webbrowser.open_new_tab(url)

        st.divider()
        st.caption("📋 Enlace directo (Copiar/Pegar):")
        st.code(url, language=None)
