import streamlit as st
import pandas as pd
import database as db

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
                st.image("images/logoInvestControl.png", use_container_width=True)
                
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
                                success, uid, uname, is_admin = db.verify_user(new_user, new_pass)
                                if success:
                                    st.session_state.authenticated = True
                                    st.session_state.user_id = uid
                                    st.session_state.username = uname
                                    st.session_state.is_admin = is_admin
                                    st.success("Administrador cadastrado!")
                                    st.rerun()
                            else:
                                st.error("As senhas não conferem.")
                        else:
                            st.error("Preencha todos os campos.")
                else:
                    with st.form("login_form"):
                        user_input = st.text_input("Email / Usuário", placeholder="seu@email.com")
                        password = st.text_input("Senha", type="password", placeholder="Sua senha")
                        submit_login = st.form_submit_button("Entrar", use_container_width=True)
                    
                    if submit_login:
                        success, uid, uname, is_admin = db.verify_user(user_input, password)
                        if success:
                            st.session_state.authenticated = True
                            st.session_state.user_id = uid
                            st.session_state.username = uname
                            st.session_state.is_admin = is_admin
                            st.rerun()
                        else:
                            st.error("Usuário ou senha incorretos.")
                
            # Link para criar conta se não for admin: posicionado abaixo das colunas para manter o alinhamento do logo com o botão Entrar
            if user_count > 0:
                st.markdown('<div style="margin-top: 12px;"></div>', unsafe_allow_html=True)
                if st.button("Não tem conta? Criar conta", use_container_width=True):
                    dialog_register_user()
    st.stop()
