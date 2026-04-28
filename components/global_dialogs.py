import streamlit as st
import pandas as pd
import time
import database as db
from utils.formatters import escape_html

@st.dialog("Seu Perfil", dismissible=False)
def dialog_user_profile():
    u_details = db.get_user_details(st.session_state.user_id)
    if u_details:
        st.markdown(f"### 👤 Perfil: `{escape_html(u_details['username'])}`")
        
        is_admin = u_details['username'] == 'admin'
        
        edit_email = st.text_input("Email", value=u_details['email'] if u_details['email'] and not pd.isna(u_details['email']) else "", disabled=is_admin)
        
        try:
            raw_birth = u_details['birth_date']
            if pd.isna(raw_birth) or not raw_birth:
                default_birth = pd.to_datetime('2000-01-01').date()
            else:
                default_birth = pd.to_datetime(raw_birth).date()
        except Exception:
            default_birth = pd.to_datetime('2000-01-01').date()
            
        edit_birth = st.date_input("Data de Nascimento", value=default_birth, min_value=pd.to_datetime('1900-01-01').date(), max_value=pd.to_datetime('today').date(), format="DD/MM/YYYY", disabled=is_admin)
        
        st.markdown("**🔐 Alterar Senha** (opcional)")
        new_pwd = st.text_input("Nova Senha", type="password", placeholder="Deixe vazio para manter atual")
        confirm_pwd = st.text_input("Confirmar Nova Senha", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Salvar Alterações", type="primary", use_container_width=True):
                if edit_email:
                    pwd_to_save = None
                    if new_pwd:
                        if new_pwd == confirm_pwd:
                            pwd_to_save = new_pwd
                        else:
                            st.error("As senhas não conferem.")
                            st.stop()
                    
                    db.update_user_profile(st.session_state.user_id, u_details['username'], edit_email, edit_birth.strftime("%Y-%m-%d"), pwd_to_save)
                    st.success("Dados atualizados com sucesso")
                    if pwd_to_save:
                        st.session_state.clear()
                        st.rerun()
                    
                    st.session_state.navigation_tab = "Visão Geral"
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("O Email é obrigatório.")
        close_perfil_dialog = False
        with col2:
            if st.button("Fechar", use_container_width=True):
                close_perfil_dialog = True
                
        if close_perfil_dialog:
            st.rerun()
            
    else:
        st.error("Erro ao carregar dados do perfil.")

@st.dialog("Importar Proventos", dismissible=False)
def dialog_importar_proventos():
    if st.session_state.get('confirm_imp_proventos', False):
        st.warning("⚠️ **Atenção:** Todos os dados de Proventos atuais deste usuário serão **APAGADOS** e substituídos pelos dados do arquivo. Deseja continuar?")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("Sim, apagar e importar", type="primary", use_container_width=True):
                arquivo = st.session_state.pop('arquivo_prov_pendente')
                with st.spinner("Aguarde a importação dos dados ser finalizada..."):
                    success, msg = db.import_proventos_csv(arquivo, st.session_state.user_id)
                if success:
                    st.success(msg)
                    st.session_state.refresh_id += 1
                    st.session_state.navigation_tab = "Proventos Recebidos"
                    st.session_state.confirm_imp_proventos = False
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error(msg)
                    st.session_state.confirm_imp_proventos = False
        with col_c2:
            if st.button("Não, cancelar", use_container_width=True):
                st.session_state.confirm_imp_proventos = False
                st.rerun()
    else:
        st.markdown("""
        A funcionalidade de importar dados de Proventos é bem simples. 
        Gere um arquivo com extensão **CSV** com o seguinte layout:

        1. **Ano** (4 caracteres no formato AAAA)
        2. **Ativo** (de 1 até 10 caracteres do tipo alfanumérico)
        3. **Janeiro** a **Dezembro** (valor recebido por ativo em cada mês)

        **Regras Importantes:**
        - Os valores devem estar sem separadores de milhares e usar `.` (ponto) como separador decimal.
        - Não use símbolos de moeda (R$, $).
        - O separador de colunas deve ser `,` (vírgula).
        """)
        
        arquivo_upload = st.file_uploader("Selecione o arquivo CSV", type=["csv"], label_visibility="collapsed", key="uploader_proventos")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Importar Dados", type="primary", use_container_width=True, disabled=(arquivo_upload is None)):
                st.session_state.confirm_imp_proventos = True
                st.session_state.arquivo_prov_pendente = arquivo_upload
                st.rerun()
        close_prov_dialog = False
        with col2:
            if st.button("Cancelar", use_container_width=True):
                close_prov_dialog = True
                
        if close_prov_dialog:
            st.rerun()

@st.dialog("Importar Ativos", dismissible=False)
def dialog_importar_ativos():

    if st.session_state.get('confirm_imp_ativos', False):
        st.warning("⚠️ **Atenção:** Todos os dados de Ativos e Histórico de Operações atuais deste usuário serão **APAGADOS** e substituídos pelos dados do arquivo. Deseja continuar?")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("Sim, apagar e importar", type="primary", use_container_width=True):
                arquivo = st.session_state.pop('arquivo_ativos_pendente')
                with st.spinner("Aguarde a importação dos dados ser finalizada..."):
                    success, msg = db.import_assets_csv(arquivo, st.session_state.user_id)
                if success:
                    st.success(msg)
                    st.session_state.refresh_id += 1
                    st.session_state.navigation_tab = "Visão Geral"
                    st.session_state.confirm_imp_ativos = False
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error(msg)
                    st.session_state.confirm_imp_ativos = False
        with col_c2:
            if st.button("Não, cancelar", use_container_width=True):
                st.session_state.confirm_imp_ativos = False
                st.rerun()
    else:
        st.markdown("""
        A funcionalidade de importar dados de Ativos é bem simples. 
        Gere um arquivo com extensão **CSV** com o seguinte layout:

        1. **Ativo** (de 1 até 10 caracteres do tipo alfanumérico)
        2. **DtOperação** (formato dd/MM/aaaa)
        3. **Quantidade** (quantidade comprada ou vendida)
        4. **Valor** (valor pago pelo ativo no momento da operação)

        **Regras Importantes:**
        - Os valores devem estar sem separadores de milhares e usar `.` (ponto) como separador decimal.
        - O separador de colunas deve ser `,` (vírgula).
        """)
        
        arquivo_upload = st.file_uploader("Selecione o arquivo CSV", type=["csv"], label_visibility="collapsed", key="uploader_ativos")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Importar Dados", type="primary", use_container_width=True, disabled=(arquivo_upload is None)):
                st.session_state.confirm_imp_ativos = True
                st.session_state.arquivo_ativos_pendente = arquivo_upload
                st.rerun()
        close_ativos_dialog = False
        with col2:
            if st.button("Cancelar", use_container_width=True):
                st.session_state.navigation_tab = "Visão Geral"
                close_ativos_dialog = True
                
        if close_ativos_dialog:
            st.rerun()

@st.dialog("Alocação de Ativos")
def dialog_alocacao_ativos():
    import database as db
    
    st.markdown("Defina o percentual de capital que deseja alocar em cada classe de ativos. A soma deve fechar em **100%**.")
    
    # Busca alocações atuais do banco
    if 'current_allocations' not in st.session_state:
        st.session_state.current_allocations = db.get_user_allocations(st.session_state.user_id)
        
    allocs = st.session_state.current_allocations
    
    # Criar form em colunas para os inputs
    col1, col2 = st.columns(2)
    with col1:
        acoes = st.number_input("Ações (%)", min_value=0.0, max_value=100.0, value=float(allocs.get('Ações', 0.0)), step=1.0)
        fiis = st.number_input("Fiis (%)", min_value=0.0, max_value=100.0, value=float(allocs.get('Fiis', 0.0)), step=1.0)
        internacionais = st.number_input("Ativos Internacionais (%)", min_value=0.0, max_value=100.0, value=float(allocs.get('Ativos Internacionais', 0.0)), step=1.0, help="Representa Stocks e Reits")
    with col2:
        criptos = st.number_input("Criptos (%)", min_value=0.0, max_value=100.0, value=float(allocs.get('Criptos', 0.0)), step=1.0)
        renda_fixa = st.number_input("Renda Fixa (%)", min_value=0.0, max_value=100.0, value=float(allocs.get('Renda Fixa', 0.0)), step=1.0)
        
    soma = acoes + fiis + internacionais + criptos + renda_fixa
    
    st.markdown("---")
    
    color = "green" if soma == 100.0 else ("red" if soma > 100.0 else "orange")
    st.markdown(f"**Soma Total:** <span style='color: {color};'>{soma:.2f}%</span>", unsafe_allow_html=True)
    
    if soma != 100.0:
        st.warning("⚠️ A soma das alocações é diferente de 100%. Isso pode gerar distorções nos futuros cálculos de balanceamento da carteira.")
        
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("Salvar", type="primary", use_container_width=True):
            new_allocs = {
                'Ações': acoes,
                'Fiis': fiis,
                'Ativos Internacionais': internacionais,
                'Criptos': criptos,
                'Renda Fixa': renda_fixa
            }
            db.save_user_allocations(st.session_state.user_id, new_allocs)
            st.session_state.pop('current_allocations', None)
            st.success("Metas de alocação salvas com sucesso!")
            st.session_state.refresh_id += 1
            import time
            time.sleep(1)
            st.rerun()
            
    with col_btn2:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.pop('current_allocations', None)
            st.rerun()
