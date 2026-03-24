import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update login
login_old = """                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user_id = uid
                        st.rerun()"""
login_new = """                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user_id = uid
                        st.session_state.is_admin = (user == 'admin')
                        st.rerun()"""
content = content.replace(login_old, login_new)

# 2. Append Admin Dashboard
admin_block = """
# ==============================
# ADMIN DASHBOARD
# ==============================
if st.session_state.get('is_admin', False):
    col_title, col_logout = st.columns([0.85, 0.15])
    with col_title:
        st.markdown('<h1 style="color: #ffffff; font-size: 2.25rem;">🛡️ Painel de Administração</h1>', unsafe_allow_html=True)
        st.markdown('<p style="color: #a1a1aa; font-size: 1rem; margin-bottom: 2rem;">Gestão de usuários do sistema.</p>', unsafe_allow_html=True)
    with col_logout:
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("Sair", use_container_width=True, key="admin_logout_top"):
            st.session_state.authenticated = False
            st.session_state.is_admin = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 1. Metricas
    users_df = db.get_all_users()
    total_users = len(users_df)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'''
        <div class="metric-card">
            <div class="metric-title">Total de Usuários</div>
            <div class="metric-value">{total_users}</div>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('<br>', unsafe_allow_html=True)
    
    # 2. Cadastro
    if st.button("➕ Novo Usuário", type="primary"):
        st.session_state.show_add_user = True
        
    @st.dialog("Criar Novo Usuário")
    def dialog_add_user():
        new_username = st.text_input("Usuário")
        new_password = st.text_input("Senha", type="password")
        if st.button("Salvar", use_container_width=True):
            if new_username and new_password:
                db.admin_create_user(new_username, new_password)
                st.success("Criado com sucesso!")
                st.session_state.show_add_user = False
                st.rerun()
            else:
                st.error("Preencha todos os campos.")
                
    if st.session_state.get('show_add_user', False):
        dialog_add_user()
        
    # 3. Tabela
    if not users_df.empty:
        st.dataframe(users_df, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="admin_users_table")
        if st.session_state.admin_users_table.selection.rows:
            row_idx = st.session_state.admin_users_table.selection.rows[0]
            user_data = users_df.iloc[row_idx]
            
            @st.dialog("Editar / Excluir Usuário")
            def dialog_edit_user(u_data):
                st.write(f"**Data de Cadastro:** {u_data['created_at']}")
                edit_username = st.text_input("Usuário", value=u_data['username'])
                edit_password = st.text_input("Nova Senha (deixe em branco para não alterar)", type="password", placeholder="*** (Criptografada)")
                
                colA, colB = st.columns(2)
                with colA:
                    if st.button("Atualizar", type="primary", use_container_width=True):
                        db.admin_update_user(int(u_data['id']), edit_username, edit_password if edit_password else None)
                        st.success("Usuário atualizado!")
                        st.rerun()
                with colB:
                    if st.button("Excluir", type="secondary", use_container_width=True):
                        if u_data['username'] == 'admin':
                            st.error("O administrador principal não pode ser excluído.")
                        else:
                            db.admin_delete_user(int(u_data['id']))
                            st.success("Excluído com sucesso!")
                            st.rerun()
                            
            dialog_edit_user(user_data)
            
    st.stop()
# ==============================
"""

content = content.replace("# Verifica e cria dashboard do próximo ano (Automated Task)", admin_block + "\\n# Verifica e cria dashboard do próximo ano (Automated Task)")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('App patched with Admin Dashboard')
