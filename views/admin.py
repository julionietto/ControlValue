# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import pandas as pd
import time
import db
from components.ui import render_top_header
from zoneinfo import ZoneInfo
from datetime import datetime

def render_admin_view():
    render_top_header("🛡️ Painel de Administração", "Gestão de usuários do sistema.")
    
    # 1. Metricas
    users_df = pd.DataFrame(db.get_all_users())
    if not users_df.empty:
        users_df = users_df.sort_values(by='id', ascending=True).reset_index(drop=True)
    if not users_df.empty and 'created_at' in users_df.columns:
        users_df['created_at_dt'] = pd.to_datetime(users_df['created_at'], errors='coerce')
        users_df['created_at'] = users_df['created_at_dt'].dt.strftime('%d/%m/%Y')
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
        
    @st.dialog("Criar Novo Usuário", dismissible=False)
    def dialog_add_user():
        new_username = st.text_input("Usuário")
        new_email = st.text_input("Email")
        new_birth = st.date_input("Data de Nascimento", format="DD/MM/YYYY")
        new_password = st.text_input("Senha", type="password")
        if st.button("Salvar", use_container_width=True):
            if new_username and new_email and new_password:
                db.admin_create_user(new_username, new_email, new_birth.strftime("%Y-%m-%d"), new_password)
                st.success("Criado com sucesso!")
                st.session_state.show_add_user = False
                st.rerun()
            else:
                st.error("Preencha todos os campos obrigatórios.")
                
    if st.session_state.get('show_add_user', False):
        dialog_add_user()
        
    # 3. Tabela
    if not users_df.empty:
        # Reordena e formata dados para exibição
        display_users = users_df.copy()
        # Calcula o status baseado no tempo atual
        sp_tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(sp_tz).replace(tzinfo=None)
        display_users['Status'] = display_users.apply(
            lambda r: "⚠️ Bloqueado" if not pd.isna(r['locked_until']) and pd.to_datetime(r['locked_until']) > now else "✔️ Ativo", 
            axis=1
        )
        
        display_users = display_users[['id', 'username', 'email', 'birth_date', 'created_at', 'Status']]
        
        # Formata a data de nascimento para dd/MM/yyyy
        display_users['birth_date'] = pd.to_datetime(display_users['birth_date'], errors='coerce').dt.strftime('%d/%m/%Y')
        display_users.columns = ['ID', 'Usuário', 'Email', 'Nascimento', 'Cadastro', 'Status']
        
        # Usamos uma chave dinâmica baseada no table_key para forçar a limpeza da seleção quando necessário
        table_key_str = f"admin_users_table_{st.session_state.get('table_key', 0)}"
        st.dataframe(display_users, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key=table_key_str)
        
        is_trigger_delete = st.session_state.get('trigger_admin_delete_user') is not None
        
        # Acessa o estado da tabela usando a chave dinâmica
        table_state = st.session_state.get(table_key_str)
        if table_state and table_state.selection.rows and not st.session_state.get('show_add_user', False) and not is_trigger_delete:
            row_idx = table_state.selection.rows[0]
            if row_idx < len(users_df):
                user_data_row = users_df.iloc[row_idx]
                
                @st.dialog("Editar / Excluir Usuário", dismissible=False)
                def dialog_edit_user(u_data):
                    st.write(f"**ID:** {u_data['id']} | **Data de Cadastro:** {u_data['created_at']}")
                    # Verifica se o usuário é o admin protegido
                    is_real_admin = (u_data['username'] == 'admin')
                    
                    try:
                        raw_date = u_data.get('birth_date')
                        if pd.isna(raw_date) or not raw_date:
                            def_birth = pd.to_datetime('2000-01-01').date()
                        else:
                            def_birth = pd.to_datetime(raw_date).date()
                    except Exception:
                        def_birth = pd.to_datetime('2000-01-01').date()
                        
                    edit_username = st.text_input("Usuário", value=u_data['username'], disabled=is_real_admin)
                    edit_email = st.text_input("Email", value=u_data['email'] if u_data['email'] and not pd.isna(u_data['email']) else "", disabled=is_real_admin)
                    edit_birth = st.date_input("Data de Nascimento", value=def_birth, min_value=pd.to_datetime('1900-01-01').date(), max_value=pd.to_datetime('today').date(), format="DD/MM/YYYY", disabled=is_real_admin)
                    edit_password = st.text_input("Nova Senha (deixe em branco para não alterar)", type="password", placeholder="*** (Criptografada)")
                    edit_password_confirm = st.text_input("Confirmar Nova Senha", type="password", placeholder="Repita a nova senha")
                    
                    # Verificação de bloqueio para exibir botão de desbloqueio
                    sp_tz = ZoneInfo("America/Sao_Paulo")
                    is_locked = not pd.isna(u_data['locked_until']) and pd.to_datetime(u_data['locked_until']) > datetime.now(sp_tz).replace(tzinfo=None)
                    if is_locked:
                        st.info(f"🚨 Este usuário está bloqueado até: {pd.to_datetime(u_data['locked_until']).strftime('%H:%M:%S de %d/%m/%Y')}")
                        if st.button("🔓 Desbloquear Usuário Manualmente", type="secondary", use_container_width=True):
                            db.admin_unlock_user(int(u_data['id']))
                            st.session_state.table_key += 1 # Limpa a seleção
                            st.success("Usuário desbloqueado com sucesso!")
                            time.sleep(1)
                            st.rerun()

                    # Validação de senhas
                    passwords_match = True
                    if edit_password:
                        if edit_password != edit_password_confirm:
                            passwords_match = False
                            st.warning("⚠️ As senhas digitadas não são iguais.")
                    
                    st.markdown('<div style="margin-top: 12px;"></div>', unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("Atualizar", type="primary", use_container_width=True, disabled=not passwords_match):
                            # Prepara dados para a confirmação final
                            st.session_state['admin_update_data'] = {
                                'id': u_data['id'],
                                'username': edit_username,
                                'email': edit_email,
                                'birth_date': edit_birth.strftime("%Y-%m-%d"),
                                'password': edit_password if edit_password else None
                            }
                            st.session_state['trigger_admin_update_user'] = True
                            st.session_state.table_key += 1 # Limpa a seleção e fecha o diálogo atual
                            st.rerun()
                    with c2:
                        if st.button("Excluir", type="secondary", use_container_width=True):
                            if u_data['username'] == 'admin':
                                st.error("O administrador principal não pode ser excluído.")
                            else:
                                st.session_state['trigger_admin_delete_user'] = u_data
                                st.session_state.table_key += 1 # Limpa a seleção para não sobrepor diálogos
                                st.rerun()
                    with c3:
                        if st.button("Cancelar", use_container_width=True):
                            st.session_state.table_key += 1 # Incrementa a chave para limpar a seleção e fechar o diálogo
                            st.rerun()
                                
                dialog_edit_user(user_data_row)
            
    # 4. Modal de Confirmação de Alteração (Independente)
    if st.session_state.get('trigger_admin_update_user'):
        update_data = st.session_state.get('admin_update_data')
        
        @st.dialog("🛡️ Confirmação de Alteração", dismissible=False)
        def dialog_confirm_update():
            st.warning(f"Você está prestes a alterar os dados do usuário **{update_data['username']}**.")
            st.markdown(f"""
            **Resumo das alterações:**
            - **Usuário:** `{update_data['username']}`
            - **Email:** `{update_data['email'] if update_data['email'] else '(Vazio)'}`
            - **Nascimento:** `{pd.to_datetime(update_data['birth_date']).strftime('%d/%m/%Y')}`
            - **Senha:** `{'Alterada (🔒)' if update_data['password'] else 'Mantida (Unchanged)'}`
            """)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Sim, Confirmar Alteração", type="primary", use_container_width=True):
                    db.admin_update_user(
                        update_data['id'], 
                        update_data['username'], 
                        update_data['email'], 
                        update_data['birth_date'], 
                        update_data['password']
                    )
                    st.session_state['trigger_admin_update_user'] = False
                    st.session_state['admin_update_data'] = None
                    st.success("Dados atualizados com sucesso!")
                    time.sleep(1)
                    st.rerun()
            with c2:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state['trigger_admin_update_user'] = False
                    st.session_state['admin_update_data'] = None
                    st.rerun()
        
        dialog_confirm_update()

    # 5. Modal de Confirmação de Exclusão (Independente)
    if 'trigger_admin_delete_user' in st.session_state and st.session_state['trigger_admin_delete_user'] is not None:
        target_user = st.session_state['trigger_admin_delete_user']
        
        @st.dialog("⚠️ Confirmação de Exclusão", dismissible=False)
        def dialog_confirm_delete():
            st.warning(f"Você está prestes a excluir permanentemente o usuário **{target_user['username']}**.")
            st.error("Aviso: Esta ação irá remover COMPLETAMENTE todos os proventos, ativos, opções e configurações vinculadas a este usuário no banco de dados. Isso não pode ser desfeito.")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Sim, Excluir Tudo", type="primary", use_container_width=True):
                    db.admin_delete_user(int(target_user['id']))
                    st.session_state['trigger_admin_delete_user'] = None
                    st.success("Usuário e todos os dados relacionados foram excluídos!")
                    time.sleep(1)
                    st.rerun()
            with c2:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state['trigger_admin_delete_user'] = None
                    st.rerun()
                    
        dialog_confirm_delete()

    st.stop()
