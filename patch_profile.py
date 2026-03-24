import re

def update_app():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update session_state login logic
    login_reg_old = '''                            st.session_state.user_id = uid
                            st.success("Usuário cadastrado!")'''
    login_reg_new = '''                            st.session_state.user_id = uid
                            st.session_state.username = new_user
                            st.success("Usuário cadastrado!")'''
    content = content.replace(login_reg_old, login_reg_new)

    login_auth_old = '''                        st.session_state.user_id = uid
                        st.session_state.is_admin = (user == 'admin')'''
    login_auth_new = '''                        st.session_state.user_id = uid
                        st.session_state.username = user
                        st.session_state.is_admin = (user == 'admin')'''
    content = content.replace(login_auth_old, login_auth_new)

    # 2. Define the exact components
    components_code = '''
# ==============================
# MENU DE PERFIL
# ==============================
@st.dialog("Seu Perfil")
def dialog_user_profile():
    u_details = db.get_user_details(st.session_state.user_id)
    if u_details:
        st.markdown(f"**Usuário:** `{u_details['username']}`")
        dt_criacao = pd.to_datetime(u_details['created_at']).strftime('%d/%m/%Y')
        st.markdown(f"**Membro desde:** `{dt_criacao}`")
    else:
        st.error("Erro ao carregar dados do perfil.")
    if st.button("Fechar", use_container_width=True):
        st.rerun()

@st.dialog("Altere sua senha")
def dialog_change_password():
    st.markdown("**Defina sua nova credencial de acesso.**")
    new_pwd = st.text_input("Nova Senha", type="password")
    confirm_pwd = st.text_input("Confirmar Nova Senha", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Salvar Senha", type="primary", use_container_width=True):
            if new_pwd and confirm_pwd:
                if new_pwd == confirm_pwd:
                    db.update_user_password(st.session_state.user_id, new_pwd)
                    st.success("Senha alterada com sucesso! Faça login novamente.")
                    st.session_state.authenticated = False
                    st.rerun()
                else:
                    st.error("As senhas não conferem.")
            else:
                st.error("Preencha todos os campos.")
    with col2:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()

def render_profile_popover():
    with st.popover(f"👤 {st.session_state.get('username', 'Perfil')}"):
        if st.button("Seu perfil", use_container_width=True):
            dialog_user_profile()
        if st.button("Altere sua senha", use_container_width=True):
            dialog_change_password()
        st.markdown("---")
        if st.button("Sair", type="primary", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.is_admin = False
            st.rerun()
'''

    # Inject components right after the session_state initializations blocks
    # We will insert it before the ADMIN DASHBOARD block starts
    target_admin_block = "# ==============================\n# ADMIN DASHBOARD"
    content = content.replace(target_admin_block, components_code + "\\n" + target_admin_block)

    # 3. Replace the logout buttons
    # Admin Logout
    admin_logout_old = '''    with col_logout:
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("Sair", use_container_width=True, key="admin_logout_top"):
            st.session_state.authenticated = False
            st.session_state.is_admin = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)'''
    
    admin_logout_new = '''    with col_logout:
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        render_profile_popover()
        st.markdown('</div>', unsafe_allow_html=True)'''
    content = content.replace(admin_logout_old, admin_logout_new)

    # Main User Logout
    user_logout_old = '''with col_logout:
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("Sair", use_container_width=True, key="btn_logout"):
        st.session_state.authenticated = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)'''
    
    user_logout_new = '''with col_logout:
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    render_profile_popover()
    st.markdown('</div>', unsafe_allow_html=True)'''
    content = content.replace(user_logout_old, user_logout_new)

    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Injected successfully!")

if __name__ == '__main__':
    update_app()
