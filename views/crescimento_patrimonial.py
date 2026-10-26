# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import plotly.graph_objects as go  # type: ignore
from plotly.subplots import make_subplots  # type: ignore
import datetime

import db
from components.ui import render_top_header, create_card
from utils.formatters import format_brl, escape_html


def get_current_portfolio_balance(user_id):
    """
    Recupera o Saldo Atual consolidado da carteira (mesma métrica exibida na Visão Geral).
    """
    if 'current_total_value' in st.session_state and st.session_state.current_total_value is not None:
        return float(st.session_state.current_total_value)
    try:
        import executive_report_service as exec_svc
        _, _, _, total_atual, _, _, _ = exec_svc.get_user_portfolio_data(user_id)
        st.session_state.current_total_value = float(total_atual)
        return float(total_atual)
    except Exception:
        return 0.0


def compute_patrimonio_growth(df):
    """
    Calcula as métricas de crescimento percentual e variação em R$ de um ano para o outro.
    Retorna o DataFrame ordenado por ano mais recente primeiro (ano DESC).
    """
    if df.empty:
        return pd.DataFrame(columns=['id', 'ano', 'valor_final', 'crescimento_pct', 'variacao_brl'])

    # Ordena cronologicamente para realizar os cálculos da evolução
    calc_df = df.copy()
    calc_df['ano'] = calc_df['ano'].astype(int)
    calc_df['valor_final'] = calc_df['valor_final'].astype(float)
    calc_df = calc_df.sort_values('ano', ascending=True).reset_index(drop=True)

    calc_df['valor_anterior'] = calc_df['valor_final'].shift(1)
    calc_df['variacao_brl'] = calc_df['valor_final'] - calc_df['valor_anterior']

    def calc_pct(row):
        prev = row['valor_anterior']
        curr = row['valor_final']
        if pd.isna(prev) or prev == 0:
            return None
        return ((curr - prev) / prev) * 100.0

    calc_df['crescimento_pct'] = calc_df.apply(calc_pct, axis=1)

    # Ordenação decrescente: o ano mais recente primeiro
    sorted_df = calc_df.sort_values('ano', ascending=False).reset_index(drop=True)
    return sorted_df


@st.dialog("➕ Adicionar Ano", dismissible=True)
def dialog_novo_patrimonio(current_balance):
    st.markdown("<h4 style='text-align: center; margin-top: -10px;'>📅 Registrar Patrimônio Anual</h4>", unsafe_allow_html=True)
    st.caption("Insira o valor patrimonial final atingido em determinado ano da sua vida financeira.")

    current_year = datetime.date.today().year
    col_y, col_v = st.columns([1, 2])
    with col_y:
        ano = st.number_input("Ano", min_value=1950, max_value=2100, value=current_year, step=1, key="input_novo_ano")
    with col_v:
        valor_default = float(st.session_state.get('novo_patrimonio_valor_temp', 0.0))
        label_val = "Valor Final (Saldo Atual em R$)" if ano == current_year else f"Valor Final em 31/12/{ano} (R$)"
        valor_final = st.number_input(
            label_val,
            min_value=0.0,
            value=valor_default,
            step=1000.0,
            format="%.2f",
            key="input_novo_valor"
        )

    if ano == current_year and current_balance > 0:
        if st.button(f"📥 Usar Saldo Atual da Carteira ({format_brl(current_balance)})", use_container_width=True):
            st.session_state.novo_patrimonio_valor_temp = float(current_balance)
            st.rerun()

    st.markdown("---")
    col_s, col_c = st.columns(2)
    with col_s:
        if st.button("💾 Salvar Registro", type="primary", use_container_width=True):
            if ano and valor_final >= 0:
                user_id = st.session_state.get('user_id', 1)
                db.save_crescimento_patrimonial(ano, valor_final, user_id)
                st.session_state.pop('novo_patrimonio_valor_temp', None)
                st.session_state.trigger_dialog_novo_patrimonio = False
                st.session_state.refresh_id = st.session_state.get('refresh_id', 0) + 1
                st.session_state.patrimonio_grid_key = st.session_state.get('patrimonio_grid_key', 0) + 1
                st.success(f"Patrimônio do ano {ano} salvo com sucesso!")
                st.rerun()
            else:
                st.error("Informe um ano e valor final válidos.")
    with col_c:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.pop('novo_patrimonio_valor_temp', None)
            st.session_state.trigger_dialog_novo_patrimonio = False
            st.session_state.patrimonio_grid_key = st.session_state.get('patrimonio_grid_key', 0) + 1
            st.rerun()


@st.dialog("Edição de Registro Patrimonial", dismissible=True)
def dialog_editar_patrimonio(df_records, preselected_id=None):
    if df_records.empty:
        st.info("Não há registros cadastrados para alteração.")
        if st.button("Fechar", use_container_width=True):
            st.session_state.trigger_dialog_editar_patrimonio = False
            st.session_state.selected_patrimonio_id = None
            st.session_state.patrimonio_grid_key = st.session_state.get('patrimonio_grid_key', 0) + 1
            st.rerun()
        return

    # Mapeamento de registros
    ano_map = {int(r['ano']): r for _, r in df_records.iterrows()}
    available_years = sorted(list(ano_map.keys()), reverse=True)

    # Identificar ano selecionado por padrão
    default_year_idx = 0
    if preselected_id is not None:
        sel_row = df_records[df_records['id'] == preselected_id]
        if not sel_row.empty:
            sel_year = int(sel_row.iloc[0]['ano'])
            if sel_year in available_years:
                default_year_idx = available_years.index(sel_year)

    selected_year = st.selectbox("Selecione o Ano", available_years, index=default_year_idx, key="edit_select_ano")
    record = ano_map[selected_year]

    val_atual = float(record['valor_final'])
    current_year = datetime.date.today().year
    label_edit = "Valor Final (Saldo Atual em R$)" if selected_year == current_year else f"Valor Final em 31/12/{selected_year} (R$)"
    novo_valor = st.number_input(label_edit, min_value=0.0, value=val_atual, step=1000.0, format="%.2f", key="edit_input_valor")

    st.markdown("---")
    col_u, col_d, col_c = st.columns([1.2, 1, 1])
    with col_u:
        if st.button("💾 Salvar", type="primary", use_container_width=True):
            user_id = st.session_state.get('user_id', 1)
            db.update_crescimento_patrimonial(int(record['id']), selected_year, novo_valor, user_id)
            st.session_state.trigger_dialog_editar_patrimonio = False
            st.session_state.selected_patrimonio_id = None
            st.session_state.refresh_id = st.session_state.get('refresh_id', 0) + 1
            st.session_state.patrimonio_grid_key = st.session_state.get('patrimonio_grid_key', 0) + 1
            st.success(f"Registro do ano {selected_year} atualizado com sucesso!")
            st.rerun()
    with col_d:
        if st.button("🗑️ Excluir", use_container_width=True):
            user_id = st.session_state.get('user_id', 1)
            db.delete_crescimento_patrimonial(int(record['id']), user_id)
            st.session_state.trigger_dialog_editar_patrimonio = False
            st.session_state.selected_patrimonio_id = None
            st.session_state.refresh_id = st.session_state.get('refresh_id', 0) + 1
            st.session_state.patrimonio_grid_key = st.session_state.get('patrimonio_grid_key', 0) + 1
            st.warning(f"Registro do ano {selected_year} excluído!")
            st.rerun()
    with col_c:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.trigger_dialog_editar_patrimonio = False
            st.session_state.selected_patrimonio_id = None
            st.session_state.patrimonio_grid_key = st.session_state.get('patrimonio_grid_key', 0) + 1
            st.rerun()


@st.dialog("🗑️ Confirmar Exclusão de Registro", dismissible=False)
def dialog_excluir_patrimonio(df_records, preselected_id=None):
    st.markdown("<h4 style='text-align: center; margin-top: -10px;'>⚠️ Excluir Registro de Patrimônio</h4>", unsafe_allow_html=True)
    if df_records.empty:
        st.info("Nenhum registro para excluir.")
        if st.button("Fechar", use_container_width=True):
            st.session_state.trigger_dialog_excluir_patrimonio = False
            st.rerun()
        return

    ano_map = {int(r['ano']): r for _, r in df_records.iterrows()}
    available_years = sorted(list(ano_map.keys()), reverse=True)
    default_year_idx = 0
    if preselected_id is not None:
        sel_row = df_records[df_records['id'] == preselected_id]
        if not sel_row.empty:
            sel_year = int(sel_row.iloc[0]['ano'])
            if sel_year in available_years:
                default_year_idx = available_years.index(sel_year)

    selected_year = st.selectbox("Ano a ser removido", available_years, index=default_year_idx, key="del_select_ano")
    record = ano_map[selected_year]

    st.warning(f"Tem certeza que deseja remover o registro patrimonial do ano **{selected_year}** ({format_brl(float(record['valor_final']))})?")
    col_y, col_n = st.columns(2)
    with col_y:
        if st.button("Sim, Excluir", type="primary", use_container_width=True):
            user_id = st.session_state.get('user_id', 1)
            db.delete_crescimento_patrimonial(int(record['id']), user_id)
            st.session_state.trigger_dialog_excluir_patrimonio = False
            st.session_state.refresh_id = st.session_state.get('refresh_id', 0) + 1
            st.success(f"Registro do ano {selected_year} removido com sucesso!")
            st.rerun()
    with col_n:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.trigger_dialog_excluir_patrimonio = False
            st.rerun()


def render_patrimonio_chart(df_chronological, is_hidden=False):
    """
    Renderiza o gráfico de barras + linha demonstrando a evolução patrimonial ao longo dos anos
    e o percentual de crescimento de um ano para o outro.
    """
    if df_chronological.empty:
        st.info("Cadastre ao menos um ano para visualizar o gráfico de crescimento patrimonial.")
        return

    anos = df_chronological['ano'].astype(str).tolist()
    valores = df_chronological['valor_final'].tolist()
    pcts = df_chronological['crescimento_pct'].tolist()
    vars_brl = df_chronological['variacao_brl'].tolist()

    # Prepara textos dos rótulos e hover
    bar_texts = []
    line_texts = []
    hover_pcts = []
    hover_vars = []

    for idx, (val, pct, v_brl) in enumerate(zip(valores, pcts, vars_brl)):
        if is_hidden:
            bar_texts.append("••••••")
            line_texts.append("••••••")
            hover_pcts.append("••••••")
            hover_vars.append("••••••")
        else:
            bar_texts.append(format_brl(val))
            if idx == 0 or pct is None or pd.isna(pct):
                line_texts.append("Base")
                hover_pcts.append("Ano Inicial")
                hover_vars.append("-")
            else:
                sinal = "+" if pct >= 0 else ""
                line_texts.append(f"{sinal}{pct:.1f}%")
                hover_pcts.append(f"{sinal}{pct:,.2f}%".replace(".", ","))
                sinal_brl = "+" if v_brl >= 0 else ""
                hover_vars.append(f"{sinal_brl}{format_brl(v_brl)}")

    # Gráfico com Eixo Secundário para % de Crescimento
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Barras de Valor Final (Patrimônio em R$)
    customdata = list(zip(bar_texts, hover_pcts, hover_vars))
    fig.add_trace(
        go.Bar(
            x=anos,
            y=valores,
            name="Valor Patrimonial (R$)",
            marker=dict(
                color="rgba(37, 99, 235, 0.85)",
                line=dict(color="#3b82f6", width=1.5)
            ),
            customdata=customdata,
            hovertemplate=(
                "<b>Ano: %{x}</b><br>"
                "Patrimônio: %{customdata[0]}<br>"
                "Crescimento: %{customdata[1]}<br>"
                "Variação: %{customdata[2]}<extra></extra>"
            ),
            text=bar_texts,
            textposition="outside",
            textfont=dict(size=11, color="#cbd5e1")
        ),
        secondary_y=False
    )

    # 2. Linha com Marcadores e Rótulos do Percentual de Crescimento
    if len(anos) > 1:
        # Preencher ponto inicial com 0 para a linha não quebrar, mas texto 'Base'
        line_y = [0.0 if (p is None or pd.isna(p)) else float(p) for p in pcts]
        line_colors = ["#00CC96" if y >= 0 else "#EF553B" for y in line_y]

        fig.add_trace(
            go.Scatter(
                x=anos,
                y=line_y,
                name="Crescimento Anual (%)",
                mode="lines+markers+text",
                line=dict(color="#00CC96", width=3, shape="spline"),
                marker=dict(size=10, color=line_colors, line=dict(color="#ffffff", width=1.5)),
                text=line_texts,
                textposition="top center",
                textfont=dict(size=12, color="#00CC96", family="Inter, sans-serif"),
                customdata=customdata,
                hovertemplate=(
                    "<b>Ano: %{x}</b><br>"
                    "Crescimento Ano a Ano: %{customdata[1]}<br>"
                    "Variação R$: %{customdata[2]}<extra></extra>"
                )
            ),
            secondary_y=True
        )

    # Ajuste de layout e temas premium
    max_val = max(valores) if valores else 100
    y_range_max = max_val * 1.25  # espaço para os rótulos acima da barra

    fig.update_layout(
        title=dict(
            text="📈 <b>Evolução do Patrimônio e Percentual de Crescimento Ano a Ano</b>",
            font=dict(size=16, color="#f8fafc")
        ),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#cbd5e1")
        ),
        hovermode="x unified",
        bargap=0.35
    )

    fig.update_xaxes(
        title="Ano",
        type="category",
        gridcolor="rgba(255, 255, 255, 0.05)",
        linecolor="rgba(255, 255, 255, 0.15)"
    )

    fig.update_yaxes(
        title="Patrimônio (R$)",
        range=[0, y_range_max],
        secondary_y=False,
        gridcolor="rgba(255, 255, 255, 0.08)",
        linecolor="rgba(255, 255, 255, 0.15)"
    )

    if len(anos) > 1:
        # Range dinâmico para a porcentagem no eixo secundário
        valid_pcts = [p for p in pcts if p is not None and not pd.isna(p)]
        min_p = min(valid_pcts) if valid_pcts else 0
        max_p = max(valid_pcts) if valid_pcts else 10
        p_margin = max(abs(max_p - min_p) * 0.3, 10)
        fig.update_yaxes(
            title="Crescimento (%)",
            ticksuffix="%",
            secondary_y=True,
            showgrid=False,
            range=[min_p - p_margin, max_p + p_margin],
            linecolor="rgba(255, 255, 255, 0.15)"
        )

    st.plotly_chart(fig, use_container_width=True)


def render_crescimento_patrimonial_view(show_header: bool = False):
    """
    Visão Principal do Crescimento Patrimonial do Investidor.
    """
    user_id = st.session_state.get('user_id', 1)
    is_hidden = st.session_state.get('hide_values', False)

    # Cabeçalho Superior Unificado (se executado como tela isolada)
    if show_header:
        render_top_header(
            "📈 Crescimento Patrimonial",
            "Acompanhe a evolução histórica do valor patrimonial ao longo da vida e o percentual de crescimento anual."
        )
    else:
        st.markdown("#### 📈 Crescimento Patrimonial")
        st.caption("Acompanhe a evolução histórica do valor patrimonial ao longo da vida e o percentual de crescimento anual.")

    # Saldo Atual da Carteira (Visão Geral)
    current_portfolio_saldo = get_current_portfolio_balance(user_id)

    # Busca o maior valor de saldo/patrimônio já registrado no banco para este investidor
    try:
        pico_historico = db.get_pico_historico(user_id)
    except Exception:
        pico_historico = current_portfolio_saldo
    pico_historico = max(pico_historico, current_portfolio_saldo)

    # Busca os dados do banco de dados
    df_raw = db.get_crescimento_patrimonial(user_id)
    current_year = datetime.date.today().year

    # Garante de forma determinística que o ano corrente na tabela e no gráfico reflita o Saldo Atual em tempo real
    if current_portfolio_saldo > 0:
        if not df_raw.empty and current_year in df_raw['ano'].values:
            df_raw.loc[df_raw['ano'] == current_year, 'valor_final'] = current_portfolio_saldo
        elif df_raw.empty or current_year not in df_raw['ano'].values:
            new_row = pd.DataFrame([{
                'id': 0,
                'user_id': user_id,
                'ano': current_year,
                'valor_final': current_portfolio_saldo,
                'created_at': datetime.datetime.now(),
                'updated_at': datetime.datetime.now()
            }])
            df_raw = pd.concat([df_raw, new_row], ignore_index=True)

    df_growth = compute_patrimonio_growth(df_raw)

    # Tratamento dos gatilhos de diálogo
    if st.session_state.pop('trigger_dialog_novo_patrimonio', False):
        dialog_novo_patrimonio(current_portfolio_saldo)

    selected_id = st.session_state.get('selected_patrimonio_id', None)
    if st.session_state.pop('trigger_dialog_editar_patrimonio', False):
        dialog_editar_patrimonio(df_growth, preselected_id=selected_id)

    # =========================================================================
    # CARDS DE KPIs RESUMIDOS (SALDO ATUAL E PICO HISTÓRICO)
    # =========================================================================
    col_k1, col_k2 = st.columns(2)

    # 1. Saldo Atual (Visão Geral)
    with col_k1:
        create_card("Saldo Atual", format_brl(current_portfolio_saldo))

    # 2. Pico Histórico (Maior saldo diário ou anual registrado no banco)
    with col_k2:
        create_card("Pico Histórico", format_brl(pico_historico) if pico_historico > 0 else "R$ 0,00")

    st.markdown("---")

    # =========================================================================
    # BARRA DE AÇÕES (APENAS "ADICIONAR ANO")
    # =========================================================================
    col_btn_novo, _ = st.columns([1.5, 6.5])
    with col_btn_novo:
        if st.button("➕ Adicionar Ano", type="primary", use_container_width=True, help="Adicionar novo registro de patrimônio"):
            st.session_state.trigger_dialog_novo_patrimonio = True
            st.rerun()

    # =========================================================================
    # TABELA DE DADOS (ORDENADA: ANO MAIS RECENTE PRIMEIRO)
    # =========================================================================
    st.markdown("### 📋 Histórico Anual de Valor Patrimonial")

    if df_growth.empty:
        st.info("Nenhum registro patrimonial cadastrado até o momento. Clique em **➕ Adicionar Ano** para inserir o primeiro ano.")
    else:
        # Prepara DataFrame para exibição formatada
        display_df = df_growth.copy()
        current_year = datetime.date.today().year

        def format_pct_display(val):
            if is_hidden: return "••••••"
            if pd.isna(val) or val is None:
                return "—"
            sinal = "+" if val >= 0 else ""
            return f"{sinal}{val:,.2f}%".replace(".", ",")

        def format_var_display(val):
            if is_hidden: return "••••••"
            if pd.isna(val) or val is None:
                return "—"
            sinal = "+" if val >= 0 else ""
            return f"{sinal}{format_brl(val)}"

        def format_val_display(val):
            if is_hidden: return "R$ ••••••"
            return format_brl(val)

        def format_ano_display(val):
            ano_int = int(val)
            if ano_int == current_year:
                return f"{ano_int} 🟢 Atual"
            return f"{ano_int}"

        display_df['Ano'] = display_df['ano'].apply(format_ano_display)
        display_df['Valor Final'] = display_df['valor_final'].apply(format_val_display)
        display_df['Crescimento (%)'] = display_df['crescimento_pct'].apply(format_pct_display)
        display_df['Variação (R$)'] = display_df['variacao_brl'].apply(format_var_display)

        # Seleção de colunas para exibição (incluindo crescimento_pct para coloração sem conflito de shape)
        cols_show = ['id', 'Ano', 'Valor Final', 'Crescimento (%)', 'Variação (R$)', 'crescimento_pct']
        table_df = display_df[cols_show].copy()

        # Estilização condicional de cores para crescimento positivo/negativo
        def style_growth(row):
            pct_raw = row.get('crescimento_pct')
            color = ''
            if pd.notna(pct_raw) and pct_raw is not None:
                color = "color: #00CC96; font-weight: bold;" if pct_raw >= 0 else "color: #EF553B; font-weight: bold;"
            target_cols = ['Crescimento (%)', 'Variação (R$)']
            return [color if col in target_cols else '' for col in row.index]

        styled_table = table_df.style \
            .apply(style_growth, axis=1) \
            .set_properties(**{'text-align': 'center'}, subset=['Ano']) \
            .set_properties(**{'text-align': 'right'}, subset=['Valor Final', 'Crescimento (%)', 'Variação (R$)'])

        col_cfg = {
            "id": None,  # Oculta ID técnico
            "crescimento_pct": None,  # Oculta coluna técnica de cálculo
            "Ano": st.column_config.TextColumn("Ano", width="small"),
            "Valor Final": st.column_config.TextColumn("Valor Final (R$)", width="medium"),
            "Crescimento (%)": st.column_config.TextColumn("Crescimento de um Ano para Outro", width="medium"),
            "Variação (R$)": st.column_config.TextColumn("Variação Anual (R$)", width="medium")
        }

        # Chave dinâmica para desmarcar a seleção ao fechar
        if 'patrimonio_grid_key' not in st.session_state:
            st.session_state.patrimonio_grid_key = 0

        grid_key = f"patrimonio_grid_{st.session_state.patrimonio_grid_key}_{st.session_state.get('refresh_id', 0)}"

        selected_table = st.dataframe(
            styled_table,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            column_config=col_cfg,
            key=grid_key
        )

        # Captura clique na linha / checkbox para abrir imediatamente a edição
        if selected_table and selected_table.selection and selected_table.selection.rows:
            sel_idx = selected_table.selection.rows[0]
            if sel_idx < len(df_growth):
                clicked_row = df_growth.iloc[sel_idx]
                st.session_state.selected_patrimonio_id = int(clicked_row['id'])
                st.session_state.trigger_dialog_editar_patrimonio = True
                # Desmarca a linha para que ao fechar nenhuma linha permaneça selecionada
                st.session_state.patrimonio_grid_key = st.session_state.get('patrimonio_grid_key', 0) + 1
                st.rerun()

    st.markdown("---")

    # =========================================================================
    # GRÁFICO DE CRESCIMENTO PATRIMONIAL (ABAIXO DA TABELA DE DADOS)
    # =========================================================================
    st.markdown("### 📊 Evolução Patrimonial ao Longo dos Anos")
    st.caption("Acompanhamento visual com o percentual de crescimento registrado ano a ano.")

    # Para o gráfico, usamos a ordem cronológica (ano mais antigo -> mais recente)
    df_chronological = df_growth.sort_values('ano', ascending=True).reset_index(drop=True) if not df_growth.empty else pd.DataFrame()
    render_patrimonio_chart(df_chronological, is_hidden=is_hidden)
