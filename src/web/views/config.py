import streamlit as st
import os
from sqlalchemy.orm import Session
from src.domain.models import UserModel
from src.core.security import verify_password, hash_password

def render(db: Session, user: UserModel, img_dir):
    c1, c2 = st.columns([1, 8])
    with c1:
        st.image(str(img_dir / "Configuracion.png"), width="stretch")
    with c2:
        st.markdown("# Configuración del Sistema")
    
    if user.role != "admin": # Basic users might need profile? Logic in app.py checked admin only for "Configuracion" tab.
        # But maybe we allow profile edit for everyone?
        # Original code: if role != "admin": Access Denied.
        # I will respect that.
        st.error("Acceso denegado.")
        return

    tab_users, tab_alerts = st.tabs(["👥 Usuarios", "🔔 Alertas (Telegram)"])
    
    with tab_users:
        st.subheader("👤 Mi Perfil")
        with st.container():
            c1, c2, c3 = st.columns([2, 2, 1])
            new_username = c1.text_input("Usuario", value=user.username)
            new_email = c2.text_input("Email", value=user.email)
            
            if c3.button("Actualizar Perfil"):
                 if new_username:
                     if new_username != user.username:
                         if db.query(UserModel).filter(UserModel.username == new_username).first():
                             st.error("¡Nombre en uso!")
                         else:
                             pass
                     try:
                         me = db.query(UserModel).filter(UserModel.id == user.id).first()
                         me.username = new_username
                         me.email = new_email
                         db.commit()
                         # Update session state proxy if needed, but app.py handles reload
                         st.success("✅ Perfil actualizado.")
                         st.rerun()
                     except Exception as e:
                         st.error(f"Error: {e}")
            
            st.markdown("#### Seguridad")
            with st.expander("🔐 Cambiar Contraseña"):
                cp_old = st.text_input("Contraseña Actual", type="password")
                cp_new = st.text_input("Nueva Contraseña", type="password")
                cp_rep = st.text_input("Repetir Nueva Contraseña", type="password")
                
                if st.button("Actualizar Contraseña"):
                    if not cp_old or not cp_new:
                        st.warning("Completa los campos.")
                    elif cp_new != cp_rep:
                        st.error("Las nuevas contraseñas no coinciden.")
                    else:
                        u_db = db.query(UserModel).filter(UserModel.id == user.id).first()
                        if verify_password(cp_old, u_db.hashed_password):
                            u_db.hashed_password = hash_password(cp_new)
                            db.commit()
                            st.success("✅ Contraseña actualizada.")
                        else:
                            st.error("La contraseña actual es incorrecta.")
        
        st.divider()
        st.subheader("Gestión de Accesos")
        
        users = db.query(UserModel).all()
        
        with st.container():
            st.caption(f"Total usuarios: {len(users)}")
            for u in users:
                c1, c2, c3, c4 = st.columns([1, 2, 1, 2])
                c1.write(f"**{u.username}**")
                c2.write(u.email)
                
                # Role Management
                role_opts = ["viewer", "admin"]
                curr_idx = role_opts.index(u.role) if u.role in role_opts else 0
                
                if u.username == "admin":
                     c3.write(f"`{u.role}` 🔒")
                else:
                    new_role = c3.selectbox("Rol", role_opts, index=curr_idx, key=f"role_{u.id}", label_visibility="collapsed")
                    if new_role != u.role:
                        u.role = new_role
                        db.commit()
                        st.toast(f"Rol de {u.username} cambiado a {new_role}")
                        st.rerun()
                
                with c4:
                     if u.username != "admin": 
                         if st.button("🗑️", key=f"del_u_{u.id}"):
                             db.delete(u)
                             db.commit()
                             st.rerun()
                         
                     new_pwd = st.text_input(f"Nueva pass para {u.username}", key=f"np_{u.id}", placeholder="Reset...")
                     if st.button("🔄 Reset", key=f"rst_{u.id}"):
                         if new_pwd:
                             u.hashed_password = hash_password(new_pwd)
                             db.commit()
                             st.success(f"Pass de {u.username} cambiada.")
                         else:
                             st.error("Escribe pass.")
                st.divider()

        st.markdown("### Crear Nuevo Usuario")
        with st.form("new_user_form"):
            c1, c2, c3 = st.columns(3)
            nu_name = c1.text_input("Usuario*")
            nu_pass = c2.text_input("Contraseña*", type="password")
            nu_role = c3.selectbox("Rol", ["viewer", "admin"])
            
            if st.form_submit_button("Crear Usuario"):
                if not nu_name or not nu_pass:
                    st.error("Usuario y contraseña requeridos.")
                else:
                    if db.query(UserModel).filter(UserModel.username == nu_name).first():
                        st.error("Usuario ya existe.")
                    else:
                        new_u = UserModel(
                            username=nu_name,
                            email="",
                            hashed_password=hash_password(nu_pass),
                            role=nu_role
                        )
                        db.add(new_u)
                        db.commit()
                        st.success("Usuario creado.")
                        st.rerun()

    with tab_alerts:
        st.subheader("Configurar Notificaciones")
        st.info("Introduce aquí los datos de tu Bot de Telegram.")
        
        current_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        current_chat = os.getenv("TELEGRAM_CHAT_ID", "")
        
        with st.form("telegram_config"):
            token_in = st.text_input("Bot Token", value=current_token, type="password")
            chat_in = st.text_input("Chat ID", value=current_chat)
            
            if st.form_submit_button("Guardar Configuración (.env)"):
                 try:
                     env_path = ".env"
                     lines = []
                     if os.path.exists(env_path):
                         with open(env_path, "r") as f:
                             lines = f.readlines()
                     
                     lines = [l for l in lines if not l.startswith("TELEGRAM_")]
                     
                     lines.append(f"\nTELEGRAM_BOT_TOKEN={token_in}\n")
                     lines.append(f"TELEGRAM_CHAT_ID={chat_in}\n")
                     
                     with open(env_path, "w") as f:
                         f.writelines(lines)
                         
                     st.success("✅ Guardado. Reinicia la aplicación.")
                 except Exception as e:
                     st.error(f"Error: {e}")
