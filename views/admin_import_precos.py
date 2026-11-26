# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import pandas as pd
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import db
from components.ui import render_top_header
from utils.formatters import escape_html, format_brl


def render_admin_import_precos_view():
    """Tela de Importação e Consulta de Ativos e Preços para o Administrador."""
    render_top_header("📥 Importar Ativos e Preços", "Upload e consulta de Preço Teto, Preço Justo e Mercado.")

    # 1. Área de Upload do Arquivo CSV
    with st.expander("📂 Carregar Novo Arquivo CSV do Dispositivo", expanded=True):
        st.markdown("""
        Selecione o arquivo CSV contendo os dados de ativos e preços de referência para o sistema.
        
        **Estrutura exigida do arquivo (4 colunas):**
        - **Código:** Código do ativo (ex: `BBAS3`, `PETR4`, `HGLG11`, `AAPL`).
        - **Preço Teto:** Valor teto sugerido para compra (ex: `35,00` ou `35.00`).
        - **Preço Justo:** Valor justo estimado do ativo (ex: `42,00` ou `42.00`).
        - **Mercado:** Identificação do mercado ou categoria (ex: `Brasil`, `EUA`, `Ações`, `FIIs`).
        
        *Dica: O sistema aceita delimitador por vírgula (`,`) ou ponto-e-vírgula (`;`), além de formatos com ponto ou vírgula decimal.*
        """)

        # Modelo para download
        sample_csv = "Código,Preço Teto,Preço Justo,Mercado\nBBAS3,35.00,42.00,Brasil\nPETR4,38.50,45.00,Brasil\nHGLG11,165.00,175.00,Brasil\nAAPL,180.00,210.00,EUA\n"
        st.download_button(
            "📥 Baixar Modelo CSV de Exemplo",
            data=sample_csv.encode('utf-8-sig'),
            file_name="modelo_ativos_precos.csv",
            mime="text/csv",
            use_container_width=False
        )

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

        col_up1, col_up2 = st.columns([3, 1], vertical_alignment="bottom")
        with col_up1:
            uploaded_file = st.file_uploader(
                "Selecione o arquivo CSV no seu notebook/dispositivo:",
                type=["csv"],
                key="uploader_ativos_precos_file"
            )
        with col_up2:
            replace_opt = st.checkbox("Substituir todos os registros anteriores", value=True)

        if st.button("🚀 Processar e Importar Arquivo", type="primary", use_container_width=True, disabled=(uploaded_file is None)):
            with st.spinner("Importando registros para a base de dados..."):
                success, msg, count = db.import_ativos_precos_csv(uploaded_file, replace_existing=replace_opt)
            if success:
                st.success(f"✅ {msg}")
                time.sleep(1.2)
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    st.markdown("<hr style='border-color: #27272a; margin: 20px 0;'>", unsafe_allow_html=True)

    # 2. Exibição dos Registros Importados na Tela
    st.markdown("### 📋 Registros Importados no Banco de Dados")

    df = db.get_all_ativos_precos()

    if df.empty:
        st.info("ℹ️ Nenhum ativo e preço importado ainda. Selecione um arquivo CSV acima para realizar a primeira importação.")
        return

    # Métricas Resumidas
    total_ativos = len(df)
    mercados_unicos = sorted(list(df['mercado'].dropna().unique()))
    qtd_mercados = len(mercados_unicos)

    # Última atualização no fuso de SP
    last_upd_str = "-"
    if 'updated_at' in df.columns and not df['updated_at'].dropna().empty:
        max_dt = pd.to_datetime(df['updated_at'].max())
        if max_dt.tzinfo is None:
            max_dt = max_dt.tz_localize('UTC')
        max_dt_sp = max_dt.tz_convert('America/Sao_Paulo')
        last_upd_str = max_dt_sp.strftime('%d/%m/%Y às %H:%M')

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.markdown(f'''
        <div class="metric-card">
            <div class="metric-title">Total de Ativos Cadastrados</div>
            <div class="metric-value">{total_ativos}</div>
        </div>
        ''', unsafe_allow_html=True)
    with col_m2:
        st.markdown(f'''
        <div class="metric-card">
            <div class="metric-title">Mercados Distintos</div>
            <div class="metric-value">{qtd_mercados}</div>
        </div>
        ''', unsafe_allow_html=True)
    with col_m3:
        st.markdown(f'''
        <div class="metric-card">
            <div class="metric-title">Última Atualização</div>
            <div class="metric-value" style="font-size: 1.15rem;">{last_upd_str}</div>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Filtros de visualização
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        search_query = st.text_input("🔍 Filtrar por Código ou Mercado:", placeholder="Ex: PETR4, Brasil, AAPL...").strip().upper()
    with col_f2:
        market_options = ["Todos"] + mercados_unicos
        selected_market = st.selectbox("Mercado:", options=market_options)

    # Aplicação dos filtros
    filtered_df = df.copy()
    if selected_market != "Todos":
        filtered_df = filtered_df[filtered_df['mercado'] == selected_market]
    if search_query:
        filtered_df = filtered_df[
            filtered_df['codigo'].str.upper().str.contains(search_query) | 
            filtered_df['mercado'].str.upper().str.contains(search_query)
        ]

    # Formatação para apresentação
    display_df = filtered_df.copy()

    # Formata datas
    if 'updated_at' in display_df.columns:
        display_df['updated_at_dt'] = pd.to_datetime(display_df['updated_at'])
        display_df['Atualizado em'] = display_df['updated_at_dt'].apply(
            lambda d: (d.tz_localize('UTC').tz_convert('America/Sao_Paulo') if d.tzinfo is None else d.tz_convert('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M') if pd.notna(d) else "-"
        )
    else:
        display_df['Atualizado em'] = "-"

    # Formata colunas de exibição
    display_df['Código'] = display_df['codigo']
    display_df['Preço Teto'] = display_df['preco_teto'].apply(lambda v: f"{v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    display_df['Preço Justo'] = display_df['preco_justo'].apply(lambda v: f"{v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    display_df['Mercado'] = display_df['mercado']

    cols_to_show = ['Código', 'Preço Teto', 'Preço Justo', 'Mercado', 'Atualizado em']
    final_table = display_df[cols_to_show].reset_index(drop=True)

    st.caption(f"Exibindo **{len(final_table)}** de **{total_ativos}** ativos cadastrados. 💡 *Clique em uma linha para editar Preço Teto e Preço Justo.*")
    
    table_key_str = f"ativos_precos_table_{st.session_state.get('table_key_precos', 0)}"
    st.dataframe(
        final_table,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key=table_key_str
    )

    # Verificação de seleção para abrir o diálogo de edição
    table_state = st.session_state.get(table_key_str)
    if table_state and table_state.selection.rows and not st.session_state.get('trigger_confirm_update_precos', False):
        row_idx = table_state.selection.rows[0]
        if row_idx < len(filtered_df):
            item_row = filtered_df.iloc[row_idx]

            @st.dialog("Editar Ativo e Preços", dismissible=False)
            def dialog_edit_ativo_preco(item):
                st.markdown(f"### ✏️ Ativo: `{escape_html(item['codigo'])}`")
                st.write(f"**Mercado:** {escape_html(item['mercado'])}")

                edit_teto = st.number_input(
                    "Preço Teto",
                    value=float(item['preco_teto']) if pd.notna(item['preco_teto']) else 0.0,
                    min_value=0.0,
                    step=0.01,
                    format="%.2f"
                )
                edit_justo = st.number_input(
                    "Preço Justo",
                    value=float(item['preco_justo']) if pd.notna(item['preco_justo']) else 0.0,
                    min_value=0.0,
                    step=0.01,
                    format="%.2f"
                )

                st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("SALVAR", type="primary", use_container_width=True):
                        db.update_ativo_preco(int(item['id']), edit_teto, edit_justo)
                        st.session_state.table_key_precos = st.session_state.get('table_key_precos', 0) + 1
                        st.success("Registro atualizado com sucesso!")
                        time.sleep(0.8)
                        st.rerun()
                with col_cancel:
                    if st.button("CANCELAR", use_container_width=True):
                        st.session_state.table_key_precos = st.session_state.get('table_key_precos', 0) + 1
                        st.rerun()

            dialog_edit_ativo_preco(item_row)

    # 3. Funcionalidade: Atualizar Preços de Ativos (Botão Vermelho com Confirmação)
    st.markdown("<hr style='border-color: #27272a; margin: 30px 0 20px 0;'>", unsafe_allow_html=True)
    st.markdown("### ⚡ Atualizar Preços de Ativos dos Usuários")
    st.markdown("""
    Clique no botão abaixo para aplicar os valores de **Preço Teto** e **Preço Justo** aos ativos de 
    **todos os usuários registrados no sistema**. 
    Para ativos com **Mercado = EUA**, a moeda de referência será definida como **USD** ($), e para **Mercado = Brasil**, como **BRL** (R$).
    """)

    # Estilização CSS do Botão com Preenchimento Vermelho
    st.markdown("""
    <style>
    div.st-key-btn_atualizar_precos_ativos button {
        background-color: #dc2626 !important;
        background: #dc2626 !important;
        color: #ffffff !important;
        border: 1px solid #b91c1c !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        padding: 0.65rem 1.25rem !important;
        border-radius: 8px !important;
        transition: all 0.2s ease-in-out !important;
    }
    div.st-key-btn_atualizar_precos_ativos button:hover {
        background-color: #b91c1c !important;
        background: #b91c1c !important;
        border-color: #991b1b !important;
        box-shadow: 0 0 14px rgba(220, 38, 38, 0.5) !important;
        transform: translateY(-1px) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.button("Atualizar Preços de Ativos", key="btn_atualizar_precos_ativos", use_container_width=True):
        st.session_state.trigger_confirm_update_precos = True

    @st.dialog("⚠️ Confirmação: Atualizar Preços de Ativos", dismissible=False)
    def dialog_confirm_update_precos():
        st.warning("⚠️ **Atenção: Ação Global no Sistema**")
        st.markdown(f"""
        Você está prestes a atualizar as carteiras de **todos os usuários** cadastrados no sistema com base na tabela atual de **Ativos e Preços** ({len(df)} ativos cadastrados).
        
        - O **Preço Teto** e o **Preço Justo** serão atualizados para cada ativo correspondente em todas as carteiras.
        - Para ativos com **Mercado = EUA**, a moeda de referência será definida como **USD** ($).
        - Para ativos com **Mercado = Brasil**, a moeda de referência será definida como **BRL** (R$).
        
        Deseja confirmar e prosseguir com a atualização?
        """)
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("Sim, Atualizar Preços", type="primary", use_container_width=True):
                with st.spinner("Atualizando registros de todos os usuários no banco de dados..."):
                    success, msg, total_upd, users_upd = db.update_user_assets_from_ativos_precos()
                st.session_state.trigger_confirm_update_precos = False
                if success:
                    st.success(f"✅ {msg}")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
        with col_c2:
            if st.button("Não, Cancelar", use_container_width=True):
                st.session_state.trigger_confirm_update_precos = False
                st.rerun()

    if st.session_state.get('trigger_confirm_update_precos', False):
        dialog_confirm_update_precos()
