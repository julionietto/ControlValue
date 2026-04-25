import streamlit as st
import pandas as pd
import database as db
import plotly.express as px
import services as svc
from utils.formatters import format_ticker_for_display, get_annual_proventos_summary, infer_asset_type
from components.ui import render_top_header

def render_proventos_view():
    render_top_header("Proventos Recebidos", "Histórico de dividendos, juros sobre capital próprio e rendimentos.")
    
    # --- Bloco de Consulta Status Invest (Sempre visível no topo) ---
    col_bt1, col_bt2 = st.columns([2, 1])
    with col_bt2:
        if st.button("🔍 Consultar Proventos Provisionados", key="btn_statusinvest_consult", use_container_width=True):
            with st.spinner("Buscando dados no Status Invest..."):
                assets_df_all = db.get_all_assets(st.session_state.user_id)
                allowed_types = ['Ações', 'Fiis', 'Stocks', 'Reits']
                
                # Prepara os ativos com seus tipos
                filtered_assets = assets_df_all[assets_df_all['asset_type'].isin(allowed_types)]
                tickers_with_types = []
                for _, row in filtered_assets.drop_duplicates(subset=['ticker']).iterrows():
                    tickers_with_types.append({
                        'ticker': row['ticker'],
                        'type': row['asset_type']
                    })
                
                if not tickers_with_types:
                    st.warning("Nenhum ativo elegível (Ações, Fiis, Stocks, Reits) na carteira.")
                else:
                    df_statusinvest, err, raw_json = svc.fetch_statusinvest_proventos(tickers_with_types)
                    if err:
                        st.error(err)
                    else:
                        st.session_state.statusinvest_results = df_statusinvest
                        st.session_state.statusinvest_raw_json = raw_json
                        st.session_state.show_statusinvest_results = True

    @st.dialog("🔍 Resposta Bruta da API (Debug)")
    def dialog_ver_json_bruto(json_data, requested_tickers):
        st.write("**Ativos enviados na requisição:**")
        st.info(", ".join(requested_tickers))
        st.write("**Abaixo está o conteúdo original retornado pelo Status Invest:**")
        st.json(json_data)
        if st.button("Fechar"):
            st.rerun()

    if st.session_state.get('show_statusinvest_results'):
        with st.expander("📅 Proventos Provisionados (Fonte: Status Invest)", expanded=True):
            col_d1, col_d2 = st.columns([3, 1])
            with col_d2:
                if st.button("🛠️ Ver JSON Bruto", use_container_width=True):
                    # Recupera os tickers brutos usados na consulta (precisamos recalcular para o dialog ou passar no session state)
                    assets_df_all = db.get_all_assets(st.session_state.user_id)
                    allowed_types = ['Ações', 'Fiis', 'Stocks', 'Reits']
                    raw_tickers = assets_df_all[assets_df_all['asset_type'].isin(allowed_types)]['ticker'].unique().tolist()
                    tickers_enviados = [t.strip().upper().replace(".SA", "") for t in raw_tickers]
                    dialog_ver_json_bruto(st.session_state.get('statusinvest_raw_json'), tickers_enviados)
            
            df_res = st.session_state.statusinvest_results
            if df_res.empty:
                st.info("Nenhum provento provisionado futuro encontrado para os ativos da sua carteira.")
            else:
                st.dataframe(df_res, hide_index=True, use_container_width=True)
                
            if st.button("Fechar Tabela", use_container_width=True):
                st.session_state.show_statusinvest_results = False
                st.rerun()
        st.markdown("---")

    proventos_df = db.get_proventos(st.session_state.user_id)
    
    meses_ordem = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    # ---- Popup: Editar Provento ----
    @st.dialog("✏️ Editar Provento", dismissible=False)
    def dialog_editar_provento(ano, ticker, df_prov):
        st.markdown(f"**Ativo:** `{format_ticker_for_display(ticker)}`  |  **Ano:** `{ano}`")
        st.markdown("---")
        selected_mes = st.selectbox("Mês", meses_ordem)
        current_val = df_prov[(df_prov['ano'] == ano) & (df_prov['ticker'] == ticker) & (df_prov['mes'] == selected_mes)]
        default_val = float(current_val['valor'].iloc[0]) if not current_val.empty else 0.0
        novo_valor = st.number_input("Valor Recebido (R$)", min_value=0.0, format="%.2f", value=default_val)
        st.markdown("")
        st.markdown("")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 Salvar", type="primary", use_container_width=True):
                db.save_provento(ano, selected_mes, ticker, novo_valor, st.session_state.user_id)
                st.session_state.refresh_id += 1
                st.rerun()
        with col2:
            if st.button("🗑️ Excluir Ativo", type="secondary", use_container_width=True):
                st.session_state.confirming_delete_provento = {'ano': ano, 'ticker': ticker}
                st.rerun()
        with col3:
            if st.button("Cancelar", use_container_width=True):
                st.rerun()

    # ---- Popup: Confirmar Exclusão Provento ----
    @st.dialog("⚠️ Confirmar Exclusão", dismissible=False)
    def dialog_confirmar_exclusao_provento(ano, ticker):
        st.warning("Tem certeza que deseja excluir este ativo da tabela dos proventos deste ano?")
        c_yes, c_no = st.columns(2)
        with c_yes:
            if st.button("Sim, confirmar", type="primary", use_container_width=True):
                db.delete_proventos_ativo_ano(ano, ticker, st.session_state.user_id)
                st.session_state.refresh_id += 1
                st.rerun()
        with c_no:
            if st.button("Não, cancelar", use_container_width=True):
                st.rerun()
    
    # ---- Popup: Adicionar Ativo ----
    @st.dialog("➕ Adicionar Ativo", dismissible=False)
    def dialog_adicionar_ativo(ano):
        st.markdown(f"**Ano de referência:** `{ano}`")
        st.markdown("---")
        ticker_novo = st.text_input("Código do Ativo (ex: PETR4.SA)").upper().strip()
        st.caption("Os valores mensais podem ser informados após a inclusão do ativo.")
        st.markdown("")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Adicionar", type="primary", use_container_width=True):
                if ticker_novo:
                    # Aplica as regras de sufixo .SA (Ações e Fiis) conhecidas
                    if len(ticker_novo) >= 4 and "." not in ticker_novo:
                        if ticker_novo not in ['BTC', 'ETH', 'SOL', 'USDT', 'USDC']:
                            ticker_novo += ".SA"
                            
                    # Cria todos os registros mensais (Janeiro a Dezembro) simultaneamente
                    for mes in meses_ordem:
                        db.save_provento(ano, mes, ticker_novo, 0.0, st.session_state.user_id)
                        
                    st.success(f"Novo ativo {ticker_novo} adicionado com sucesso !")
                    st.session_state.refresh_id += 1
                    import time
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.warning("Informe o código do ativo.")
        with col2:
            if st.button("Cancelar", use_container_width=True):
                st.rerun()
    
    # ---- Aciona popups se houver estado ativo ----
    if st.session_state.get('confirming_delete_provento'):
        c_data = st.session_state.pop('confirming_delete_provento')
        dialog_confirmar_exclusao_provento(c_data['ano'], c_data['ticker'])
        
    if st.session_state.get('editing_provento'):
        edit_data = st.session_state.pop('editing_provento')
        if edit_data['ticker'] == '__NOVO__':
            dialog_adicionar_ativo(edit_data['ano'])
        else:
            dialog_editar_provento(edit_data['ano'], edit_data['ticker'], proventos_df)
    
    # ---- Dashboard principal ----
    if proventos_df.empty:
        st.info("Nenhum dado de provento registrado. Por favor, importe o arquivo Proventos.csv na barra lateral.")
    else:
        tab_mensal, tab_ranking = st.tabs(["Histórico Mensal", "🏆 Ranking de Pagadores"])
        with tab_mensal:
            def format_provento(val):
                if pd.isna(val) or val == 0:
                    return "0,00"
                return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                
            ano_atual = pd.Timestamp.now().year
            anos_disponiveis = sorted([int(a) for a in proventos_df['ano'].unique()], reverse=True)
            
            import base64
            import os
            growth_icon_tag = "📈"
            tooltip_text = "Essa linha informa o percentual de crescimento de dividendos comparado com o mesmo período do ano anterior."
            icon_path = os.path.join(os.path.dirname(__file__), "..", "images", "growth_icon.png") # Caminho atualizado
            if os.path.exists(icon_path):
                with open(icon_path, "rb") as f:
                    b64_str = base64.b64encode(f.read()).decode()
                    growth_icon_tag = f'<img src="data:image/png;base64,{b64_str}" width="28" title="{tooltip_text}">'
            else:
                growth_icon_tag = f'<span title="{tooltip_text}">📈</span>'
            
            for ano in anos_disponiveis:
                st.markdown(f"**Ano:** {ano}")
                
                df_ano = proventos_df[proventos_df['ano'] == ano]
                pivot_df = df_ano.pivot_table(index='ticker', columns='mes', values='valor', aggfunc='sum').fillna(0)
                
                for mes in meses_ordem:
                    if mes not in pivot_df.columns:
                        pivot_df[mes] = 0.0
                
                pivot_df = pivot_df[meses_ordem].sort_index()
                
                pivot_df['Valor Anual'] = pivot_df.sum(axis=1)
                pivot_df['Valor Mensal'] = pivot_df['Valor Anual'] / 12
                col_order = meses_ordem + ['Valor Mensal', 'Valor Anual']
                pivot_df = pivot_df[col_order]
                
                totais_row = pivot_df.sum(axis=0)
                
                display_df = pivot_df.copy()
                for col in display_df.columns:
                    display_df[col] = display_df[col].apply(format_provento)
                display_df = display_df.reset_index()
                display_df['OriginalTicker'] = display_df['ticker']
                display_df['ticker'] = display_df['ticker'].apply(format_ticker_for_display)
                display_df.rename(columns={'ticker': 'Ativo'}, inplace=True)
                
                key_df = f"prov_df_{ano}_{st.session_state.refresh_id}"
                
                cols_right = [col for col in col_order]
                styled_df = display_df.style.set_properties(**{'text-align': 'center'}, subset=['Ativo']) \
                                           .set_properties(**{'text-align': 'right'}, subset=cols_right) \
                                           .set_properties(**{'color': '#00CC96'}, subset=['Valor Mensal']) \
                                           .set_properties(**{'color': '#3d9df3'}, subset=['Valor Anual'])

                selected = st.dataframe(
                    styled_df,
                    hide_index=True,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    column_config={"OriginalTicker": None},
                    key=key_df
                )
                
                if selected.selection.rows:
                    row_idx = selected.selection.rows[0]
                    ticker_selecionado = display_df.iloc[row_idx]['OriginalTicker']
                    st.session_state.editing_provento = {'ano': ano, 'ticker': ticker_selecionado}
                    st.rerun()

                st.markdown("""
                    <style>
                    .growth-positive { color: #00CC96 !important; }
                    .growth-negative { color: #EF553B !important; }
                    th { font-weight: normal !important; font-size: 0.85rem; }
                    td { font-size: 0.85rem; }
                    </style>
                """, unsafe_allow_html=True)

                footer_rows = []
                tm_row = {'Mês': 'TOTAL'}
                style_val = 'font-weight: normal; font-size: 0.85rem; text-align: right;'
                for col in col_order:
                    color_total = ''
                    if col == 'Valor Mensal': color_total = 'color: #00CC96;'
                    elif col == 'Valor Anual': color_total = 'color: #3d9df3;'
                    
                    val_fmt = format_provento(totais_row[col])
                    tm_row[col] = f'<div style="{style_val} {color_total}">{val_fmt}</div>'
                footer_rows.append(tm_row)
                
                ano_mais_antigo = min(anos_disponiveis)
                if ano > ano_mais_antigo:
                    prev_year = ano - 1
                    df_prev = proventos_df[proventos_df['ano'] == prev_year]
                    pivot_prev = df_prev.pivot_table(index='ticker', columns='mes', values='valor', aggfunc='sum').fillna(0)
                    for mes in meses_ordem:
                        if mes not in pivot_prev.columns:
                            pivot_prev[mes] = 0.0
                    
                    totais_prev = pivot_prev[meses_ordem].sum(axis=0)
                    res_final_prev = totais_prev.sum()
                    media_prev = res_final_prev / 12
                    
                    totais_prev_full = totais_prev.copy()
                    totais_prev_full['Valor Mensal'] = media_prev
                    totais_prev_full['Valor Anual'] = res_final_prev
                    
                    growth_row = {'Mês': growth_icon_tag}
                    for col in col_order:
                        val_curr = totais_row[col]
                        val_prev = totais_prev_full[col]
                        
                        style_val = 'font-weight: normal; font-size: 0.85rem; text-align: right;'
                        
                        if val_prev > 0:
                            pct = ((val_curr / val_prev) - 1) * 100
                            color = "#00CC96" if pct >= 0 else "red"
                            growth_row[col] = f'<div style="color: {color}; {style_val}">{pct:,.2f}%</div>'.replace('.', ',')
                        else:
                            growth_row[col] = f'<div style="{style_val}">0,00%</div>'
                    footer_rows.append(growth_row)

                if ano == ano_atual:
                    now = pd.Timestamp.now()
                    mes_atual_idx = now.month
                    mes_atual_nome = meses_ordem[mes_atual_idx-1]
                    
                    avg_ytd_row = {'Mês': f'<div style="font-size: 0.8rem; white-space: nowrap;">Média até {mes_atual_nome}</div>'}
                    
                    proventos_ytd = totais_row[meses_ordem[:mes_atual_idx]].sum()
                    media_ytd = proventos_ytd / mes_atual_idx
                    
                    for col in col_order:
                        if col == 'Valor Mensal':
                            val_fmt = format_provento(media_ytd)
                            avg_ytd_row[col] = f'<div style="font-weight: bold; font-size: 0.85rem; text-align: right; color: #00CC96;">{val_fmt}</div>'
                        elif col == 'Valor Anual':
                            avg_ytd_row[col] = ''
                        else:
                            avg_ytd_row[col] = ''
                    footer_rows.append(avg_ytd_row)

                df_footer = pd.DataFrame(footer_rows)
                df_footer['Mês'] = df_footer['Mês'].replace('Valor Mensal', '<span style="font-size: 0.8rem;">Valor Mensal</span>')
                
                st.write(df_footer.to_html(escape=False, index=False), unsafe_allow_html=True)
                
                if ano == ano_atual:
                    st.markdown("")
                    if st.button("➕ Adicionar Ativo", key=f"add_ativo_{ano}"):
                        st.session_state.editing_provento = {'ano': ano, 'ticker': '__NOVO__'}
                        st.rerun()
                        
                st.markdown("<br>", unsafe_allow_html=True)

            # ---- Dashboard de Resumo Anual ----
            st.markdown("---")
            st.markdown('<h3 style="color: #ffffff; font-size: 1.2rem; margin-bottom: 1rem;">📊 Resumo Anual de Proventos</h3>', unsafe_allow_html=True)

            resumo_df = get_annual_proventos_summary(proventos_df, anos_disponiveis)
            
            if not resumo_df.empty:
                meses_cols = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                display_resumo = resumo_df.copy()
                for m in meses_cols:
                    display_resumo[m] = display_resumo[m].apply(format_provento)
                display_resumo['Valor Mensal'] = display_resumo['Valor Mensal'].apply(format_provento)
                display_resumo['Valor Anual'] = display_resumo['Valor Anual'].apply(format_provento)
                
                display_resumo.rename(columns={'Valor Anual': 'Valor Anual '}, inplace=True)
                
                cols_resumo = ['Ano'] + meses_cols + ['Valor Mensal', 'Valor Anual ']
                display_resumo = display_resumo[cols_resumo]

                global_max_val = resumo_df[meses_cols].values.max()

                def highlight_absolute_max(s):
                    if s.name in meses_cols:
                        idx_s = s.index
                        res = []
                        for i in idx_s:
                            val_num = resumo_df.loc[i, s.name]
                            res.append('color: #00CC96' if (val_num == global_max_val and global_max_val > 0) else '')
                        return res
                    return ['' for _ in s]

                styled_resumo = display_resumo.style.apply(highlight_absolute_max, axis=0) \
                                              .set_properties(**{'text-align': 'center'}, subset=['Ano']) \
                                              .set_properties(**{'text-align': 'right'}, subset=meses_cols + ['Valor Mensal', 'Valor Anual ']) \
                                              .set_properties(**{'color': '#00CC96'}, subset=['Valor Mensal']) \
                                              .set_properties(**{'color': '#3d9df3'}, subset=['Valor Anual '])

                st.dataframe(styled_resumo, hide_index=True, use_container_width=True)

                # ---- Tabela de Proventos Stocks e Reits ----
                assets_df_all = db.get_all_assets(st.session_state.user_id) 
                has_us_assets_active = not assets_df_all[assets_df_all['asset_type'].isin(['Stocks', 'Reits'])].empty

                if has_us_assets_active:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<h3 style="color: #ffffff; font-size: 1.2rem; margin-bottom: 1rem;">Proventos Recebidos de ativos dolarizados. (Valores em R$)</h3>', unsafe_allow_html=True)
                    
                    with db.get_db_connection() as conn:
                        full_assets_map = {row['ticker']: row['asset_type'] for _, row in pd.read_sql_query("SELECT ticker, asset_type FROM assets", conn).iterrows()}
                    
                    all_hist_tickers = proventos_df['ticker'].unique()
                    us_tickers = [t for t in all_hist_tickers if full_assets_map.get(t, infer_asset_type(t)) in ['Stocks', 'Reits']]
                    df_us_prov = proventos_df[proventos_df['ticker'].isin(us_tickers)]
                    
                    if not df_us_prov.empty:
                        resumo_us = df_us_prov.groupby('ano')['valor'].sum().reset_index()
                        resumo_us.columns = ['Ano', 'Valor']
                        resumo_us['Ano'] = resumo_us['Ano'].astype(str)
                        resumo_us = resumo_us.sort_values('Ano', ascending=True)
                        
                        display_us = resumo_us.copy()
                        display_us['Valor'] = display_us['Valor'].apply(format_provento)
                        
                        styled_us = display_us.style.set_properties(**{'text-align': 'center'}, subset=['Ano']) \
                                                   .set_properties(**{'text-align': 'right'}, subset=['Valor'])
                        
                        st.dataframe(
                            styled_us, 
                            hide_index=True, 
                            use_container_width=True,
                            column_config={
                                "Ano": st.column_config.TextColumn(width="small"),
                                "Valor": st.column_config.TextColumn(width="small")
                            }
                        )
                    else:
                        st.info("Nenhum provento de Stocks ou Reits registrado.")


        with tab_ranking:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<h3 style='color: #ffffff; font-size: 1.2rem; margin-bottom: 1rem;'>Top Pagadores de Dividendos</h3>", unsafe_allow_html=True)
            
            ano_selecionado = st.selectbox("Selecione o Ano", anos_disponiveis, key="ano_ranking_prov")
            
            df_ano_ranking = proventos_df[proventos_df['ano'] == ano_selecionado].copy()
            
            if not df_ano_ranking.empty:
                ranking_df = df_ano_ranking.groupby('ticker')['valor'].sum().reset_index()
                ranking_df.rename(columns={'valor': 'Valor Anual', 'ticker': 'Ativo'}, inplace=True)
                ranking_df['Ativo'] = ranking_df['Ativo'].apply(format_ticker_for_display)
                ranking_df = ranking_df.sort_values(by='Valor Anual', ascending=False).reset_index(drop=True)
                ranking_df.index = ranking_df.index + 1
                ranking_df = ranking_df.reset_index().rename(columns={'index': 'Posição'})
                
                max_val = ranking_df['Valor Anual'].max()
                fig = px.bar(
                    ranking_df,
                    x='Ativo', 
                    y='Valor Anual',
                    text_auto='.2f',
                    color='Valor Anual',
                    color_continuous_scale='tempo',
                    template='plotly_dark'
                )
                
                fig.update_traces(
                    textfont_size=12,
                    textangle=0,
                    textposition="outside",
                    cliponaxis=False,
                    marker_line_color="#1f1f1f",
                    marker_line_width=1,
                    opacity=0.9
                )
                
                fig.update_layout(
                    margin=dict(l=20, r=20, t=30, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    coloraxis_showscale=False,
                    xaxis=dict(title=""),
                    yaxis=dict(title="Valor Anual (R$)", range=[0, max_val * 1.15], showgrid=True, gridcolor="#333333"),
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                ranking_display = ranking_df.copy()
                ranking_display['Posição'] = ranking_display['Posição'].apply(lambda x: f"#{x}")
                ranking_display['Valor Anual'] = ranking_display['Valor Anual'].apply(lambda val: f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                
                styled_rank = ranking_display.style.set_properties(**{'text-align': 'center'}, subset=['Posição', 'Ativo'])\
                                                 .set_properties(**{'text-align': 'right'}, subset=['Valor Anual'])
                
                st.dataframe(styled_rank, hide_index=True, use_container_width=True)
            else:
                st.info(f"Nenhum provento registrado para o ano {ano_selecionado}.")

    st.stop()
