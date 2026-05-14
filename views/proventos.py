# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import db
import plotly.express as px  # type: ignore # pyrefly: ignore[missing-import]
import services as svc
from utils.formatters import format_ticker_for_display, get_annual_proventos_summary, infer_asset_type
from components.ui import render_top_header

def render_proventos_view():
    render_top_header("Proventos Recebidos", "Histórico de dividendos, juros sobre capital próprio e rendimentos.")
    
    # --- Bloco de Consulta Status Invest (Sempre visível no topo) ---
    col_bt1, col_bt2 = st.columns([2, 1])
    with col_bt2:
        last_sync = db.get_last_sync_log()
        sync_msg = "Ainda não sincronizado."
        if last_sync:
            # last_sync['execution_time'] is a datetime object
            # Garantindo a conversão para o fuso horário de São Paulo
            sync_dt_obj = pd.to_datetime(last_sync['execution_time'])
            if sync_dt_obj.tzinfo is None:
                sync_dt_obj = sync_dt_obj.tz_localize('UTC')
            sync_dt_sp = sync_dt_obj.tz_convert('America/Sao_Paulo')
            
            sync_dt = sync_dt_sp.strftime('%d/%m/%Y às %H:%M')
            status_text = "sucesso" if last_sync['status'] == 'SUCCESS' else "com erro"
            sync_msg = f"Última sincronização diária: {sync_dt} ({status_text})"
            
        st.caption(f"☁️ {sync_msg}")

        if st.button("🔍 Proventos Futuros", key="btn_statusinvest_consult", use_container_width=True):
            st.session_state.show_statusinvest_results = True

    if st.session_state.get('show_statusinvest_results'):
        with st.expander("📅 Proventos Provisionados (Rotina Diária)", expanded=True):
            prov_df = db.get_proventos_provisionados_calculados(st.session_state.user_id)
            if prov_df.empty:
                st.info("Nenhum provento provisionado futuro encontrado para os ativos da sua carteira no momento.")
            else:
                # Formata as datas para o padrão brasileiro DD/MM/YYYY
                prov_df['data_com'] = pd.to_datetime(prov_df['data_com']).dt.strftime('%d/%m/%Y')
                prov_df['data_pagamento'] = pd.to_datetime(prov_df['data_pagamento']).dt.strftime('%d/%m/%Y')
                
                # Limpa o sufixo .SA visualmente
                prov_df['ticker'] = prov_df['ticker'].str.replace('.SA', '', regex=False)
                
                # Calcula o Total a Receber
                prov_df['Total a Receber'] = prov_df['valor'] * prov_df['quantidade_elegivel']
                
                prov_df = prov_df.rename(columns={
                    'ticker': 'Ativo',
                    'tipo': 'Tipo',
                    'data_com': 'Data Com',
                    'data_pagamento': 'Data Pagamento',
                    'valor': 'Valor Cota (R$)',
                    'quantidade_elegivel': 'Qtd (Data Com)'
                })
                
                # Remove colunas indesejadas (id, user_id) se existirem
                cols_to_drop = [c for c in ['id', 'user_id'] if c in prov_df.columns]
                prov_df = prov_df.drop(columns=cols_to_drop)
                
                is_hidden = st.session_state.get('hide_values', False)
                # Calcula o Total a Receber original
                total_provisionado = prov_df['Total a Receber'].sum()
                
                if is_hidden:
                    prov_df['Valor Cota (R$)'] = "R$ ••••••"
                    prov_df['Qtd (Data Com)'] = "••••••"
                    prov_df['Total a Receber'] = "R$ ••••••"
                    
                st.success("Estes são os valores futuros mapeados com base na sua posição até a Data Com:")
                
                if is_hidden:
                    styled_prov = prov_df.style.set_properties(**{'text-align': 'center'}) \
                          .set_table_styles([dict(selector='th', props=[('text-align', 'center')])])
                else:
                    styled_prov = prov_df.style.format({
                            'Valor Cota (R$)': 'R$ {:.4f}',
                            'Qtd (Data Com)': '{:,.0f}',
                            'Total a Receber': 'R$ {:.2f}'
                        }).set_properties(**{'text-align': 'center'}) \
                          .set_table_styles([dict(selector='th', props=[('text-align', 'center')])])
                    
                st.dataframe(
                    styled_prov,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Totalizador
                st.markdown("<br>", unsafe_allow_html=True)
                col_f1, col_f2 = st.columns([1, 1])
                with col_f1:
                    if st.button("Fechar Tabela", use_container_width=True):
                        st.session_state.show_statusinvest_results = False
                        st.rerun()
                with col_f2:
                    total_fmt = "R$ ••••••" if is_hidden else f"R$ {total_provisionado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    st.markdown(f"<div style='text-align: right; font-size: 1.2rem; font-weight: bold; color: #00CC96; padding-top: 5px;'>Total: {total_fmt}</div>", unsafe_allow_html=True)
        st.markdown("---")

    proventos_df = db.get_proventos(st.session_state.user_id)
    
    # Busca ativos ativos (quantidade > 0) para destacar os inativos
    assets_df = db.get_all_assets(st.session_state.user_id)
    active_tickers = set(assets_df[assets_df['quantity'] > 0]['ticker'].unique()) if not assets_df.empty else set()
    
    meses_nomes_dict = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    meses_ordem = list(meses_nomes_dict.values())
    meses_nums = list(meses_nomes_dict.keys())
    
    # ---- Popup: Editar Provento ----
    @st.dialog("✏️ Editar Provento", dismissible=False)
    def dialog_editar_provento(ano, ticker, df_prov):
        st.markdown(f"**Ativo:** `{format_ticker_for_display(ticker)}`  |  **Ano:** `{ano}`")
        st.markdown("---")
        
        mes_key = f"mes_edit_prov_{ano}_{ticker}"
        if mes_key not in st.session_state:
            st.session_state[mes_key] = meses_ordem[0]
            
        val_id_key = f"val_id_edit_prov_{ano}_{ticker}"
        if val_id_key not in st.session_state:
            st.session_state[val_id_key] = 0
            
        def on_month_change():
            st.session_state[val_id_key] += 1

        selected_mes_nome = st.selectbox("Mês", meses_ordem, key=mes_key, on_change=on_month_change)
        selected_mes_num = {v: k for k, v in meses_nomes_dict.items()}[selected_mes_nome]
        
        current_val = df_prov[(df_prov['ano'] == ano) & (df_prov['ticker'] == ticker) & (df_prov['mes'] == selected_mes_num)]
        default_val = float(current_val['valor'].iloc[0]) if not current_val.empty else 0.0
            
        dynamic_val_key = f"val_edit_prov_{ano}_{ticker}_{st.session_state[val_id_key]}"
        novo_valor = st.number_input("Valor Recebido (R$)", min_value=0.0, format="%.2f", value=default_val, key=dynamic_val_key)
        st.markdown("*<small style='color: #888;'>Pressione Enter ou Tab no teclado após digitar para aplicar o novo valor antes de salvar.</small>*", unsafe_allow_html=True)
        
        st.markdown("")
        st.markdown("")
        
        def clear_state():
            if mes_key in st.session_state: del st.session_state[mes_key]
            if val_id_key in st.session_state: del st.session_state[val_id_key]
            for k in list(st.session_state.keys()):
                if k.startswith(f"val_edit_prov_{ano}_{ticker}_"):
                    del st.session_state[k]

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 Salvar", use_container_width=True):
                db.save_provento(ano, selected_mes_num, ticker, novo_valor, st.session_state.user_id)
                st.session_state.refresh_id += 1
                clear_state()
                st.rerun()
        with col2:
            if st.button("🗑️ Excluir Ativo", use_container_width=True):
                st.session_state.confirming_delete_provento = {'ano': ano, 'ticker': ticker}
                clear_state()
                st.rerun()
        with col3:
            if st.button("Cancelar", use_container_width=True):
                clear_state()
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
                            
                    # Cria todos os registros mensais (1 a 12) simultaneamente
                    for mes_num in meses_nums:
                        db.save_provento(ano, mes_num, ticker_novo, 0.0, st.session_state.user_id)
                        
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
                if st.session_state.get('hide_values', False): return "••••••"
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
                pivot_df = pivot_df.rename(columns=meses_nomes_dict)
                
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
                
                def style_row(row):
                    is_active = row['OriginalTicker'] in active_tickers
                    if not is_active and ano == ano_atual:
                        return ['color: #EF553B'] * len(row)
                    
                    # Cores para ativos ativos
                    colors = []
                    for col in row.index:
                        if col == 'Valor Mensal':
                            colors.append('color: #00CC96')
                        elif col == 'Valor Anual':
                            colors.append('color: #3d9df3')
                        else:
                            colors.append('')
                    return colors

                styled_df = display_df.style.apply(style_row, axis=1) \
                                           .set_properties(**{'text-align': 'center'}, subset=['Ativo']) \
                                           .set_properties(**{'text-align': 'right'}, subset=cols_right)

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
                    st.session_state.refresh_id += 1
                    st.rerun()

                st.markdown("""
                    <style>
                    .growth-positive { color: #00CC96 !important; }
                    .growth-negative { color: #EF553B !important; }
                    th { font-weight: normal !important; font-size: 0.85rem; }
                    th:first-child { text-align: center !important; }
                    td { font-size: 0.85rem; }
                    </style>
                """, unsafe_allow_html=True)

                footer_rows = []
                tm_row = {'MÊS': '<div style="text-align: center;">TOTAL</div>'}
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
                    pivot_prev = pivot_prev.rename(columns=meses_nomes_dict)
                    
                    for mes in meses_ordem:
                        if mes not in pivot_prev.columns:
                            pivot_prev[mes] = 0.0
                    
                    totais_prev = pivot_prev[meses_ordem].sum(axis=0)
                    res_final_prev = totais_prev.sum()
                    media_prev = res_final_prev / 12
                    
                    totais_prev_full = totais_prev.copy()
                    totais_prev_full['Valor Mensal'] = media_prev
                    totais_prev_full['Valor Anual'] = res_final_prev
                    
                    growth_row = {'MÊS': f'<div style="text-align: center;">{growth_icon_tag}</div>'}
                    for col in col_order:
                        val_curr = totais_row[col]
                        val_prev = totais_prev_full[col]
                        
                        style_val = 'font-weight: normal; font-size: 0.85rem; text-align: right;'
                        
                        if st.session_state.get('hide_values', False):
                            growth_row[col] = f'<div style="{style_val}">••••••</div>'
                        elif val_prev > 0:
                            pct = ((val_curr / val_prev) - 1) * 100
                            color = "#00CC96" if pct >= 0 else "red"
                            growth_row[col] = f'<div style="color: {color}; {style_val}">{pct:,.2f}%</div>'.replace('.', ',')
                        else:
                            growth_row[col] = f'<div style="{style_val}">0,00%</div>'
                    footer_rows.append(growth_row)

                if ano == ano_atual:
                    now = pd.Timestamp.now()
                    mes_atual_idx = now.month
                    
                    avg_ytd_row = {'MÊS': f'<div style="text-align: center; font-size: 0.8rem; white-space: nowrap;">MÉDIA ACUMULADA</div>'}
                    
                    # Para cada mês até o atual, calcula a média acumulada (Jan, Jan+Fev/2, Jan+Fev+Mar/3...)
                    # Os valores são exibidos em verde (#00CC96)
                    for i, mes_nome in enumerate(meses_ordem):
                        if i < mes_atual_idx:
                            num_meses = i + 1
                            soma_acumulada = totais_row[meses_ordem[:num_meses]].sum()
                            media_mes = soma_acumulada / num_meses
                            val_fmt = format_provento(media_mes)
                            avg_ytd_row[mes_nome] = f'<div style="font-size: 0.85rem; text-align: right; color: #00CC96;">{val_fmt}</div>'
                        else:
                            avg_ytd_row[mes_nome] = ''
                    
                    # Colunas finais (vazias conforme solicitado, pois o valor já consta no mês atual)
                    avg_ytd_row['Valor Mensal'] = ''
                    avg_ytd_row['Valor Anual'] = ''
                    
                    footer_rows.append(avg_ytd_row)

                df_footer = pd.DataFrame(footer_rows)
                df_footer['MÊS'] = df_footer['MÊS'].replace('Valor Mensal', '<span style="font-size: 0.8rem;">Valor Mensal</span>')
                
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
                
                if st.session_state.get('hide_values', False):
                    st.info("📊 Gráfico oculto para privacidade.")
                else:
                    st.plotly_chart(fig, use_container_width=True)
                
                ranking_display = ranking_df.copy()
                ranking_display['Posição'] = ranking_display['Posição'].apply(lambda x: f"#{x}")
                is_hidden = st.session_state.get('hide_values', False)
                ranking_display['Valor Anual'] = ranking_display['Valor Anual'].apply(lambda val: "R$ ••••••" if is_hidden else f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                
                styled_rank = ranking_display.style.set_properties(**{'text-align': 'center'}, subset=['Posição', 'Ativo'])\
                                                 .set_properties(**{'text-align': 'right'}, subset=['Valor Anual'])
                
                st.dataframe(styled_rank, hide_index=True, use_container_width=True)
            else:
                st.info(f"Nenhum provento registrado para o ano {ano_selecionado}.")

    st.stop()
