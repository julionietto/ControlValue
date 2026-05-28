# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import db
import os
import secrets
import services as svc

@st.dialog("Recuperar Senha")
def dialog_recuperar_senha():
    st.markdown("### 🔑 Redefinição de Senha")
    st.write("Informe o seu e-mail de cadastro. Se ele existir em nossa base, enviaremos um link para você redefinir sua senha.")
    
    rec_email = st.text_input("E-mail", placeholder="seu@email.com")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Enviar Link", type="primary", use_container_width=True):
            if rec_email:
                user_info = db.get_user_by_email(rec_email)
                if user_info:
                    token = secrets.token_urlsafe(32)
                    db.create_password_reset_token(user_info['id'], token, 30)
                    
                    base_url = "https://controlvalue-o2ayzvj6exmtbyskbxhvqn.streamlit.app"
                    try:
                        # Fallback for local testing
                        if "localhost" in st.context.headers.get("Host", ""):
                            base_url = "http://localhost:8501"
                    except Exception as e:
                        import logging
                        logging.warning(f"Aviso ao determinar host: {e}")
                        
                    reset_link = f"{base_url}/?token={token}"
                    success, msg = svc.send_password_reset_email(rec_email, reset_link)
                    
                    if success:
                        st.success("Se o e-mail existir em nossa base, um link de recuperação foi enviado.")
                    else:
                        st.error(msg)
                else:
                    # Generic message to avoid email enumeration
                    st.success("Se o e-mail existir em nossa base, um link de recuperação foi enviado.")
            else:
                st.error("Informe um e-mail válido.")
                
    with col2:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()

def render_reset_password_view(token):
    _, login_col, _ = st.columns([0.15, 0.7, 0.15])
    
    with login_col:
        with st.container(border=True):
            st.markdown('<h1 style="text-align: left; margin-top: 0; margin-bottom: 24px; font-size: 2.25rem; font-weight: 700; color: #ffffff;">🔑 Nova Senha</h1>', unsafe_allow_html=True)
            
            is_valid, user_id, msg = db.verify_password_reset_token(token)
            
            if not is_valid:
                st.error(msg)
                if st.button("Voltar ao Login", use_container_width=True):
                    st.query_params.clear()
                    st.rerun()
            else:
                with st.form("reset_password_form"):
                    new_pass = st.text_input("Nova Senha", type="password", placeholder="Sua nova senha")
                    confirm_pass = st.text_input("Confirmar Nova Senha", type="password", placeholder="Repita a senha")
                    submit_reset = st.form_submit_button("Redefinir Senha", use_container_width=True)
                    
                if submit_reset:
                    if new_pass and confirm_pass:
                        if new_pass == confirm_pass:
                            success, reset_msg = db.reset_password_with_token(token, new_pass)
                            if success:
                                st.success(reset_msg)
                                st.query_params.clear()
                                st.info("Sua senha foi atualizada. Você já pode fazer login.")
                            else:
                                st.error(reset_msg)
                        else:
                            st.error("As senhas não conferem.")
                    else:
                        st.error("Preencha todos os campos.")
                
                st.markdown('<div style="margin-top: 12px;"></div>', unsafe_allow_html=True)
                if st.button("Cancelar e Voltar ao Login", use_container_width=True):
                    st.query_params.clear()
                    st.rerun()
    st.stop()

@st.dialog("Criar Conta", dismissible=False)
def dialog_register_user():
    st.markdown("### 📝 Cadastre-se")
    reg_username = st.text_input("Nome de Usuário", placeholder="Como quer ser chamado")
    reg_email = st.text_input("Email", placeholder="seu@email.com")
    reg_birth = st.date_input("Data de Nascimento", min_value=pd.to_datetime('1900-01-01').date(), max_value=pd.to_datetime('today').date(), format="DD/MM/YYYY")
    reg_pass = st.text_input("Senha", type="password", placeholder="Sua senha")
    reg_confirm = st.text_input("Confirmar Senha", type="password", placeholder="Repita a senha")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Criar Conta", type="primary", use_container_width=True):
            if reg_username and reg_email and reg_pass:
                if reg_username.lower().strip() == 'admin':
                    st.error("O nome de usuário 'admin' é reservado.")
                elif reg_pass == reg_confirm:
                    db.create_user(reg_username, reg_email, reg_birth.strftime("%Y-%m-%d"), reg_pass)
                    st.success("Conta criada com sucesso! Faça login.")
                    st.rerun()
                else:
                    st.error("As senhas não conferem.")
            else:
                st.error("Preencha todos os campos obrigatórios.")
    close_login_dialog = False
    with col2:
        if st.button("Cancelar", use_container_width=True):
            close_login_dialog = True
            
    if close_login_dialog:
        st.rerun()

def render_auth_view():
    # Centraliza o login usando colunas [15%, 70%, 15%]
    _, login_col, _ = st.columns([0.15, 0.7, 0.15])
    
    with login_col:
        # Usamos um container com borda para criar o efeito de card de forma nativa e limpa
        with st.container(border=True):
            col_logo, col_form = st.columns([0.6, 0.4], gap="medium", vertical_alignment="bottom")
            
            with col_logo:
                # Links sociais acima do logo
                images_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")
                ig_login_path = os.path.join(images_dir, "logo-instagram.jpg")
                em_login_path = os.path.join(images_dir, "logo-email.png")
                
                try:
                    import base64
                    # Instagram
                    with open(ig_login_path, "rb") as f:
                        ig_login_b64 = base64.b64encode(f.read()).decode()
                    # E-mail
                    with open(em_login_path, "rb") as f:
                        em_login_b64 = base64.b64encode(f.read()).decode()
                        
                    st.markdown(
                        f"""
                        <div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 24px;">
                            <a href="https://www.instagram.com/controlvalueoficial/" target="_blank" style="text-decoration: none;">
                                <div class="social-link" style="width: 67px; height: 67px; border-radius: 14px;">
                                    <img src="data:image/jpeg;base64,{ig_login_b64}" width="38" height="38" style="object-fit: contain;">
                                </div>
                            </a>
                            <a href="mailto:controlvalueoficial@gmail.com" style="text-decoration: none;">
                                <div class="social-link" style="width: 67px; height: 67px; border-radius: 14px;">
                                    <img src="data:image/png;base64,{em_login_b64}" width="38" height="38" style="object-fit: contain;">
                                </div>
                            </a>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                except Exception as e:
                    import logging
                    logging.warning(f"Aviso ao renderizar links sociais: {e}")

                # Resolve o caminho da imagem de forma robusta
                logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "logoControlValue.png")
                if os.path.exists(logo_path):
                    st.image(logo_path, use_container_width=True)
                else:
                    st.error(f"Logo não encontrado em: {logo_path}")
                
            with col_form:
                st.markdown('<h1 style="text-align: left; margin-top: 0; margin-bottom: 24px; font-size: 2.25rem; font-weight: 700; color: #ffffff;">🔐 Acesso</h1>', unsafe_allow_html=True)
                
                user_count = db.get_user_count()
                
                if user_count == 0:
                    st.info("Nenhum usuário cadastrado. Crie sua conta de administrador.")
                    with st.form("register_form_admin"):
                        new_user = st.text_input("Usuário", value="admin", disabled=True)
                        new_email = st.text_input("Email", placeholder="seu@email.com")
                        new_birth = st.date_input("Data de Nascimento", format="DD/MM/YYYY")
                        new_pass = st.text_input("Senha", type="password", placeholder="Sua senha")
                        confirm_pass = st.text_input("Confirmar", type="password", placeholder="Repita a senha")
                        submit_reg = st.form_submit_button("Criar Conta de Admin", use_container_width=True)
                    
                    if submit_reg:
                        if new_user and new_email and new_pass:
                            if new_pass == confirm_pass:
                                db.create_user(new_user, "admin@system", "1900-01-01", new_pass) # Placeholder for first-time admin setup if needed
                                success, uid, uname, is_admin, status, extra, theme_pref = db.verify_user(new_user, new_pass)
                                if success:
                                    st.session_state.authenticated = True
                                    st.session_state.user_id = uid
                                    st.session_state.username = uname
                                    st.session_state.is_admin = is_admin
                                    st.session_state.theme_preference = theme_pref
                                    st.success("Administrador cadastrado!")
                                    st.rerun()
                            else:
                                st.error("As senhas não conferem.")
                        else:
                            st.error("Preencha todos os campos.")
                else:
                    user_input = st.text_input("Email / Usuário", placeholder="seu@email.com")
                    password = st.text_input("Senha", type="password", placeholder="Sua senha")
                    submit_login = st.button("Entrar", use_container_width=True)
                    
                    if submit_login:
                        success, uid, uname, is_admin, status, extra, theme_pref = db.verify_user(user_input, password)
                        if success:
                            st.session_state.authenticated = True
                            st.session_state.user_id = uid
                            st.session_state.username = uname
                            st.session_state.is_admin = is_admin
                            st.session_state.theme_preference = theme_pref
                            st.rerun()
                        else:
                            if status == 'LOCKED':
                                st.error("Seu acesso está bloqueado por 3 tentativas de login recusadas. Entre em contato com administrador do sistema ou aguarde alguns instantes para tentar o login novamente.")
                            elif status == 'WRONG_PASS':
                                # Busca o usuário para saber quantas tentativas restam (opcional, mantendo o aviso de erro)
                                st.error("Usuário ou senha incorretos.")
                            else:
                                st.error("Usuário não encontrado.")
                
            # Link para criar conta se não for admin: posicionado abaixo das colunas para manter o alinhamento do logo com o botão Entrar
            if user_count > 0:
                st.markdown('<div style="margin-top: 12px;"></div>', unsafe_allow_html=True)
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Não tem conta? Criar", use_container_width=True):
                        dialog_register_user()
                with col_btn2:
                    if st.button("Esqueci minha senha", use_container_width=True):
                        dialog_recuperar_senha()
    st.stop()
