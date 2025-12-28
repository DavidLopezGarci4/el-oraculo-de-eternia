import streamlit as st
from sqlalchemy.orm import Session
from src.infrastructure.repositories.product import ProductRepository
from src.web.shared import toggle_ownership

def render(db: Session, img_dir, user, repo: ProductRepository):
    from src.domain.models import OfferModel, PendingMatchModel, BlackcludedItemModel
    # Header
    c1, c2 = st.columns([1, 8])
    with c1:
        st.image(str(img_dir / "cazador_ofertas.png"), width="stretch") 
    with c2:
        st.markdown("# Cazador de Ofertas 🔥")
    
    st.caption("Rastreando bajadas de precio superiores al 20% respecto al máximo histórico.")
    
    # --- Filters ---
    # Default to 120 as requested
    max_p_filter = st.slider("Precio Máximo Original (Filtrar ofertas caras)", 0, 500, 120, step=10, help="Solo muestra ofertas cuyo precio original era inferior a este valor.")
    
    # Efficient SQL Filter
    deals = repo.get_active_deals(min_discount=0.20, max_original_price=max_p_filter)
    
    if not deals:
        st.info("El Cazador no ha encontrado presas hoy. Vuelve más tarde o ajusta el filtro.")
        return

    st.success(f"¡Se han avistado {len(deals)} oportunidades!")
    
    # Info on Linking
    with st.expander("ℹ️ ¿Por qué veo ofertas incorrectas?", expanded=False):
        st.write("""
        Las ofertas se asocian automáticamente si el nombre en la tienda se parece mucho al de tu base de datos (Matching Difuso).
        A veces, el sistema se confunde (ej: "He-Man" vs "He-Man Battle Armor").
        
        **Cómo arreglarlo:**
        - **↩️ Desvincular**: Envía la oferta al **Purgatorio**, donde podrás unirla manualmente al producto correcto.
        - **🚫 Banear**: Si el link es basura o spam, bloquéalo para siempre.
        """)

    current_user_id = user.id
    
    # Grid Layout
    cols = st.columns(3)
    for idx, (product, offer, discount) in enumerate(deals):
        with cols[idx % 3]:
            with st.container(border=True):
                # Image
                if product.image_url:
                    st.image(product.image_url, width="stretch")
                
                st.subheader(product.name)
                
                # Prices
                st.markdown(f"**{offer.price:.2f}€**")
                st.caption(f"Antes: ~{offer.max_price:.2f}€~")
                from src.web.shared import render_external_link
                render_external_link(offer.url, shop_name=offer.shop_name, price=offer.price, key_suffix=f"hunt_{offer.id}")
                
                # Actions
                c_act1, c_act2 = st.columns(2)
                
                # Add to Collection
                # 1. Check Optimistic State
                if "optimistic_updates" not in st.session_state:
                    st.session_state.optimistic_updates = {}
                
                # Check Local Override first, then DB
                is_owned_db = any(i.owner_id == current_user_id for i in product.collection_items)
                if product.id in st.session_state.optimistic_updates:
                     is_owned = st.session_state.optimistic_updates[product.id]
                else:
                     is_owned = is_owned_db

                if is_owned:
                    c_act1.button("✅ En Colección", key=f"deal_owned_{offer.id}", disabled=True)
                else:
                    btn_label = "➕ Capturar"
                    if c_act1.button(btn_label, key=f"hunter_add_{product.id}", width="stretch"):
                        # Optimistic Update
                        st.session_state.optimistic_updates[product.id] = True
                        
                        if toggle_ownership(db, product.id, current_user_id):
                            st.rerun()

                # Cleanup Actions (Popover for safety/cleanliness)
                with c_act2.popover("🗑️ Opciones"):
                     st.write("**Gestión de Enlace**")
                     if st.button("↩️ Desvincular (Purgatorio)", key=f"h_unlink_{offer.id}"):
                         try:
                             # Duplicate Logic from Admin (Move to Pending)
                             # Re-fetch to ensure session validity
                             target_o = db.query(OfferModel).filter(OfferModel.id == offer.id).first()
                             if target_o:
                                 # Create Pending
                                 pending = PendingMatchModel(
                                         scraped_name=product.name, # Use product name context
                                         price=target_o.price,
                                         currency=target_o.currency,
                                         url=target_o.url,
                                         shop_name=target_o.shop_name,
                                         image_url=product.image_url
                                 )
                                 db.add(pending)
                                 db.delete(target_o)
                                 db.commit()
                                 st.toast("Oferta enviada al Purgatorio.")
                                 st.rerun()
                         except Exception as e:
                             db.rollback()
                             st.error(f"Error: {e}")

                     if st.button("🚫 Banear URL", key=f"h_ban_{offer.id}"):
                         try:
                             target_o = db.query(OfferModel).filter(OfferModel.id == offer.id).first()
                             if target_o:
                                 # Check existence first to be safe, but also handle race condition via try/except
                                 exists = db.query(BlackcludedItemModel).filter(BlackcludedItemModel.url == target_o.url).first()
                                 if not exists:
                                     bl = BlackcludedItemModel(
                                         url=target_o.url,
                                         scraped_name=product.name,
                                         reason="hunter_ban"
                                     )
                                     db.add(bl)
                                 
                                 # Always delete the offer
                                 db.delete(target_o)
                                 db.commit()
                                 st.toast("Oferta bloqueada y eliminada.")
                                 st.rerun()
                         except Exception as e:
                             db.rollback()
                             # Should we retry deleting the offer if only the insert failed?
                             # Simpler: just show error. But user wants solution.
                             # If error contains "UNIQUE constraint", we can assume it's already banned and just delete offer.
                             if "UNIQUE constraint" in str(e):
                                 try:
                                     # Retry delete only
                                     target_o = db.query(OfferModel).filter(OfferModel.id == offer.id).first()
                                     if target_o:
                                         db.delete(target_o)
                                         db.commit()
                                         st.toast("Oferta eliminada (Ya estaba en Blacklist).")
                                         st.rerun()
                                 except Exception as e2:
                                     st.error(f"Error forzado: {e2}")
                             else:
                                 st.error(f"Error al banear: {e}")
