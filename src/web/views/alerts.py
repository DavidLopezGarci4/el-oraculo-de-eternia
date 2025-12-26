import streamlit as st
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

def render(db: Session, user, img_dir):
    from src.domain.models import ProductModel, PriceAlertModel, UserModel
    c1, c2 = st.columns([1, 8])
    with c1:
        st.image(str(img_dir / "centinela.png"), width="stretch") # Asset específico del Centinela
    with c2:
        st.markdown("# El Centinela")
    st.caption("Gestiona tus vigilancias de precios y no dejes escapar ninguna reliquia.")
    
    st.divider()
    
    tab_list, tab_create = st.tabs(["📡 Vigilancias Activas", "➕ Nueva Alerta"])
    
    with tab_list:
        alerts = db.query(PriceAlertModel).options(
            joinedload(PriceAlertModel.product).joinedload(ProductModel.offers)
        ).filter(PriceAlertModel.user_id == user.id).all()
        if not alerts:
            st.info("No tienes centinelas activos. Añade uno desde el catálogo o la pestaña 'Nueva Alerta'.")
        else:
            for a in alerts:
                with st.container(border=True):
                    c_info, c_price, c_act = st.columns([3, 1, 1])
                    with c_info:
                        st.markdown(f"**{a.product.name}**")
                        st.caption(f"Categoría: {a.product.category}")
                    with c_price:
                        # Obtener mejor precio actual
                        best_p = 0.0
                        if a.product.offers:
                            prices = [o.price for o in a.product.offers if o.price > 0]
                            if prices: best_p = min(prices)
                        
                        st.metric("Objetivo", f"{a.target_price:.2f}€", delta=f"{best_p - a.target_price:.2f}€" if best_p > 0 else None, delta_color="inverse")
                    with c_act:
                        if st.button("🗑️ Detener", key=f"del_alert_{a.id}"):
                            db.delete(a)
                            db.commit()
                            st.toast("Centinela retirado.")
                            st.rerun()

    with tab_create:
        st.subheader("Desplegar nuevo Centinela")
        # Selector de producto con carga ansiosa de ofertas para evitar DetachedInstanceError
        all_products = db.query(ProductModel).options(joinedload(ProductModel.offers)).order_by(ProductModel.name).all()
        target_p = st.selectbox("Selecciona la figura a vigilar", all_products, format_func=lambda x: x.name)
        
        if target_p:
            c1, c2 = st.columns(2)
            # Mostrar precio actual como referencia
            best_curr = 0.0
            if target_p.offers:
                prices = [o.price for o in target_p.offers if o.price > 0]
                if prices: best_curr = min(prices)
            
            c1.metric("Precio Actual", f"{best_curr:.2f}€" if best_curr > 0 else "---")
            
            t_price = c2.number_input("Precio Objetivo (€)", min_value=1.0, value=max(1.0, best_curr * 0.9), step=1.0)
            
            if st.button("🚀 Activar Centinela", type="primary", use_container_width=True):
                # Verificar si ya existe
                exists = db.query(PriceAlertModel).filter(
                    PriceAlertModel.user_id == user.id,
                    PriceAlertModel.product_id == target_p.id
                ).first()
                if exists:
                    st.warning("Ya tienes un centinela para esta figura.")
                else:
                    new_alert = PriceAlertModel(
                        user_id=user.id,
                        product_id=target_p.id,
                        target_price=t_price
                    )
                    db.add(new_alert)
                    db.commit()
                    st.success(f"Centinela desplegado para {target_p.name}")
                    st.rerun()
