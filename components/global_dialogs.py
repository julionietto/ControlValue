# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import pandas as pd
import time
import db
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
        
        with col2:
            if st.button("Fechar", use_container_width=True):
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
    import db
    
    st.markdown("Defina o percentual de capital que deseja alocar em cada classe de ativos. A soma deve fechar em **100%**.")
    
    # Busca alocações desejadas (metas) do banco
    if 'current_allocations' not in st.session_state:
        st.session_state.current_allocations = db.get_user_allocations(st.session_state.user_id)
    allocs = st.session_state.current_allocations
    
    # Busca percentuais atuais (calculados na Visão Geral)
    current_allocs_pct = st.session_state.get('current_allocs_pct', {
        'Ações': 0.0, 'Fiis': 0.0, 'Ativos Internacionais': 0.0, 'Criptos': 0.0, 'Renda Fixa': 0.0
    })
    
    # Header da "Tabela"
    st.markdown("---")
    col_h1, col_h2, col_h3 = st.columns([1.2, 1.5, 1])
    col_h1.markdown("**Tipo de Ativo**")
    col_h2.markdown("<div style='text-align: center;'><b>Desejado (%)</b></div>", unsafe_allow_html=True)
    col_h3.markdown("<div style='text-align: center;'><b>Atual (%)</b></div>", unsafe_allow_html=True)
    
    classes = [
        ('Ações', 'Ações'),
        ('Fiis', 'Fiis'),
        ('Ativos Internacionais', 'Internacionais'),
        ('Criptos', 'Criptos'),
        ('Renda Fixa', 'Renda Fixa')
    ]
    
    new_values = {}
    
    for db_key, display_label in classes:
        c1, c2, c3 = st.columns([1.2, 1.5, 1])
        c1.write(display_label)
        
        # Percentual Desejado (Editável)
        val_desejado = c2.number_input(
            f"Metas_{db_key}", 
            min_value=0.0, 
            max_value=100.0, 
            value=float(allocs.get(db_key, 0.0)), 
            step=1.0, 
            format="%.2f",
            label_visibility="collapsed",
            key=f"input_alloc_{db_key}"
        )
        new_values[db_key] = val_desejado
        
        # Percentual Atual
        val_atual = current_allocs_pct.get(db_key, 0.0)
        # Cor vermelha (#EF553B) se o atual for maior que o desejado
        color = "#EF553B" if val_atual > val_desejado else "#a1a1aa"
        c3.markdown(f"<div style='color: {color}; text-align: center; font-weight: bold; margin-top: 5px;'>{val_atual:.2f}%</div>", unsafe_allow_html=True)

    # Cálculo da soma das metas
    soma = sum(new_values.values())
    
    st.markdown("---")
    
    color_soma = "green" if soma == 100.0 else "red"
    st.markdown(f"**Soma das Metas:** <span style='color: {color_soma}; font-weight: bold;'>{soma:.2f}%</span>", unsafe_allow_html=True)
    
    if soma != 100.0:
        st.error(f"⚠️ A soma das metas deve ser exatamente **100%**. (Soma atual: {soma:.2f}%)")
        
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("Salvar", type="primary", use_container_width=True, disabled=(soma != 100.0)):
            db.save_user_allocations(st.session_state.user_id, new_values)
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

@st.dialog("Preferências")
def dialog_preferencias():
    st.markdown("### 🎨 Preferências Visuais")
    st.write("Escolha o tema que mais lhe agrada. O sistema será atualizado automaticamente com a sua escolha.")
    
    theme_options = {
        'original': 'Original',
        'cyberpunk': 'Cyberpunk / Neon',
        'glassmorphism': 'Glassmorphism Pastel',
        'minimalista': 'Minimalista'
    }
    
    # Usa o tema default 'cyberpunk' caso não encontre
    current_theme = st.session_state.get('theme_preference', 'cyberpunk')
    
    theme_keys = list(theme_options.keys())
    try:
        current_idx = theme_keys.index(current_theme)
    except ValueError:
        current_idx = 1 # cyberpunk default index
        
    selected_theme_label = st.radio(
        "Temas Disponíveis:",
        options=list(theme_options.values()),
        index=current_idx
    )
    
    selected_theme_key = next(k for k, v in theme_options.items() if v == selected_theme_label)
    
    # Se o usuário escolheu e clicou em Salvar
    status_placeholder = st.empty()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Salvar", type="primary", use_container_width=True):
            status_placeholder.info("⏳ Aguarde enquanto estamos atualizando o tema...")
            
            # O st.spinner força o Streamlit a enviar a mensagem acima imediatamente para o navegador
            with st.spinner(""):
                # time.sleep(1.0) # Pausa para dar tempo da mensagem ser lida
                db.update_user_theme(st.session_state.user_id, selected_theme_key)
                st.session_state.theme_preference = selected_theme_key
            
            status_placeholder.empty()
            status_placeholder.success("Alteração realizada com sucesso!")
            time.sleep(1.5)
            st.rerun()
            
    with col2:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()
