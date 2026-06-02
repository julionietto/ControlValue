# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import db
import services as svc
from utils.formatters import format_ticker_for_display
from components.ui import render_top_header

def render_proventos_historico_view():
    render_top_header("🗓️ Histórico Mensal", "Detalhamento de proventos recebidos por ativo e ano.")
    
    # --- Bloco de Consulta Investidor10 ---
    col_bt1, col_bt2 = st.columns([2, 1])
    with col_bt2:
        last_sync = db.get_last_sync_log()
        sync_msg = "Ainda não sincronizado."
        if last_sync:
            sync_dt_obj = pd.to_datetime(last_sync['execution_time'])
            if sync_dt_obj.tzinfo is None:
                sync_dt_obj = sync_dt_obj.tz_localize('UTC')
            sync_dt_sp = sync_dt_obj.tz_convert('America/Sao_Paulo')
            sync_dt = sync_dt_sp.strftime('%d/%m/%Y às %H:%M')
            status_text = "sucesso" if last_sync['status'] == 'SUCCESS' else "com erro"
            sync_msg = f"Última sincronização diária: {sync_dt} ({status_text})"
        st.caption(f"☁️ {sync_msg}")

        if st.button("🔍 Proventos Futuros", key="btn_investidor10_consult", use_container_width=True):
            st.session_state.show_investidor10_results = True

    if st.session_state.get('show_investidor10_results'):
        with st.expander("📅 Proventos Provisionados (Rotina Diária)", expanded=True):
            prov_df = db.get_proventos_provisionados_calculados(st.session_state.user_id)
            if prov_df.empty:
                st.info("Nenhum provento provisionado futuro encontrado.")
            else:
                prov_df['data_com'] = pd.to_datetime(prov_df['data_com']).dt.strftime('%d/%m/%Y')
                prov_df['data_pagamento'] = pd.to_datetime(prov_df['data_pagamento']).dt.strftime('%d/%m/%Y')
                prov_df['ticker'] = prov_df['ticker'].str.replace('.SA', '', regex=False)
                prov_df['Total a Receber'] = prov_df['valor'] * prov_df['quantidade_elegivel']
                
                prov_df = prov_df.rename(columns={
                    'ticker': 'Ativo', 'tipo': 'Tipo', 'data_com': 'Data Com',
                    'data_pagamento': 'Data Pagamento', 'valor': 'Valor Cota (R$)',
                    'quantidade_elegivel': 'Qtd (Data Com)'
                })
                
                cols_to_drop = [c for c in ['id', 'user_id'] if c in prov_df.columns]
                prov_df = prov_df.drop(columns=cols_to_drop)
                
                is_hidden = st.session_state.get('hide_values', False)
                total_provisionado = prov_df['Total a Receber'].sum()
                
                if is_hidden:
                    prov_df['Valor Cota (R$)'] = "R$ ••••••"
                    prov_df['Qtd (Data Com)'] = "••••••"
                    prov_df['Total a Receber'] = "R$ ••••••"
                    
                if is_hidden:
                    styled_prov = prov_df.style.set_properties(**{'text-align': 'center'})
                else:
                    styled_prov = prov_df.style.format({
                            'Valor Cota (R$)': 'R$ {:.4f}',
                            'Qtd (Data Com)': '{:,.0f}',
                            'Total a Receber': 'R$ {:.2f}'
                        }).set_properties(**{'text-align': 'center'})
                    
                st.dataframe(styled_prov, use_container_width=True, hide_index=True)
                
                col_f1, col_f2 = st.columns([1, 1])
                with col_f1:
                    if st.button("Fechar Tabela", use_container_width=True):
                        st.session_state.show_investidor10_results = False
                        st.rerun()
                with col_f2:
                    total_fmt = "R$ ••••••" if is_hidden else f"R$ {total_provisionado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    st.markdown(f"<div style='text-align: right; font-size: 1.2rem; font-weight: bold; color: #00CC96; padding-top: 5px;'>Total: {total_fmt}</div>", unsafe_allow_html=True)
        st.markdown("---")

    proventos_df = db.get_proventos(st.session_state.user_id)
    if proventos_df.empty:
        st.info("Nenhum dado de provento registrado.")
        return

    assets_df = db.get_all_assets(st.session_state.user_id)
    active_tickers = set(assets_df[assets_df['quantity'] > 0]['ticker'].unique()) if not assets_df.empty else set()
    
    meses_nomes_dict = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    meses_ordem = list(meses_nomes_dict.values())
    meses_nums = list(meses_nomes_dict.keys())

    # ---- Dialogs ----
    @st.dialog("✏️ Editar Provento", dismissible=False)
    def dialog_editar_provento(ano, ticker, df_prov):
        st.markdown(f"**Ativo:** `{format_ticker_for_display(ticker)}`  |  **Ano:** `{ano}`")
        st.markdown("---")
        mes_key, val_id_key, prev_mes_key = f"me_{ano}_{ticker}", f"vi_{ano}_{ticker}", f"pm_{ano}_{ticker}"
        if val_id_key not in st.session_state: st.session_state[val_id_key] = 0
        col_m, col_v = st.columns(2)
        with col_m:
            selected_mes_nome = st.selectbox("Mês", meses_ordem, key=mes_key)
            
        if prev_mes_key not in st.session_state: st.session_state[prev_mes_key] = selected_mes_nome
        elif st.session_state[prev_mes_key] != selected_mes_nome:
            st.session_state[val_id_key] += 1
            st.session_state[prev_mes_key] = selected_mes_nome
        selected_mes_num = {v: k for k, v in meses_nomes_dict.items()}[selected_mes_nome]
        current_val = df_prov[(df_prov['ano'] == ano) & (df_prov['ticker'] == ticker) & (df_prov['mes'] == selected_mes_num)]
        default_val = float(current_val['valor'].iloc[0]) if not current_val.empty else 0.0
        dynamic_val_key = f"ve_{ano}_{ticker}_{st.session_state[val_id_key]}"
        
        with col_v:
            novo_valor = st.number_input("Valor Recebido (R$)", min_value=0.0, format="%.2f", value=default_val, key=dynamic_val_key)
        
        def clear_state():
            for k in [mes_key, prev_mes_key, val_id_key, 'editing_provento']:
                if k in st.session_state: del st.session_state[k]
            for k in list(st.session_state.keys()):
                if k.startswith(f"ve_{ano}_{ticker}_"): del st.session_state[k]

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("💾 Salvar", use_container_width=True):
                db.save_provento(ano, selected_mes_num, ticker, novo_valor, st.session_state.user_id)
                st.session_state.refresh_id += 1
                clear_state(); st.rerun()
        with c2:
            if st.button("🗑️ Excluir", use_container_width=True):
                st.session_state.confirming_delete_provento = {'ano': ano, 'ticker': ticker}
                clear_state(); st.rerun()
        with c3:
            if st.button("Cancelar", use_container_width=True):
                clear_state(); st.rerun()

    @st.dialog("➕ Adicionar Ativo", dismissible=False)
    def dialog_adicionar_ativo(ano):
        st.markdown(f"**Ano:** `{ano}`")
        ticker_novo = st.text_input("Código do Ativo").upper().strip()
        if st.button("✅ Adicionar", type="primary", use_container_width=True):
            if ticker_novo:
                if len(ticker_novo) >= 4 and "." not in ticker_novo and ticker_novo not in ['BTC', 'ETH', 'SOL', 'USDT', 'USDC']:
                    ticker_novo += ".SA"
                for m in meses_nums: db.save_provento(ano, m, ticker_novo, 0.0, st.session_state.user_id)
                st.session_state.refresh_id += 1
                if 'editing_provento' in st.session_state: del st.session_state['editing_provento']
                st.rerun()

    # ---- Trigger Popups ----
    if st.session_state.get('editing_provento'):
        edit_data = st.session_state['editing_provento']
        if edit_data['ticker'] == '__NOVO__': dialog_adicionar_ativo(edit_data['ano'])
        else: dialog_editar_provento(edit_data['ano'], edit_data['ticker'], proventos_df)

    # ---- Main Table Logic ----
    # Seleção de Ano (Reduzida para ~10%)
    anos_disponiveis = sorted([int(a) for a in proventos_df['ano'].unique()], reverse=True)
    col_sel, col_empty = st.columns([0.10, 0.90])
    with col_sel:
        ano = st.selectbox("Selecione o Ano", anos_disponiveis, key="sel_ano_detalhe")
    
    def format_provento(val):
        if st.session_state.get('hide_values', False): return "••••••"
        return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not pd.isna(val) and val != 0 else "0,00"

    df_ano = proventos_df[proventos_df['ano'] == ano]
    pivot_df = df_ano.pivot_table(index='ticker', columns='mes', values='valor', aggfunc='sum').fillna(0)
    pivot_df = pivot_df.rename(columns=meses_nomes_dict)
    for mes in meses_ordem:
        if mes not in pivot_df.columns: pivot_df[mes] = 0.0
    pivot_df = pivot_df[meses_ordem].sort_index()
    pivot_df['Valor Anual'] = pivot_df.sum(axis=1)
    pivot_df['Valor Mensal'] = pivot_df['Valor Anual'] / 12
    col_order = meses_ordem + ['Valor Mensal', 'Valor Anual']
    pivot_df = pivot_df[col_order]
    totais_row = pivot_df.sum(axis=0)
    
    display_df = pivot_df.copy()
    for col in display_df.columns: display_df[col] = display_df[col].apply(format_provento)
    display_df = display_df.reset_index()
    display_df['OriginalTicker'] = display_df['ticker']
    display_df['ticker'] = display_df['ticker'].apply(format_ticker_for_display)
    display_df.rename(columns={'ticker': 'Ativo'}, inplace=True)
    
    def style_row(row):
        is_active = row['OriginalTicker'] in active_tickers
        now = pd.Timestamp.now()
        is_current_year = (ano == now.year)
        current_month_name = meses_nomes_dict.get(now.month)
        
        styles = []
        for col in row.index:
            col_styles = []
            
            # Destaca os valores do mês atual com fonte laranja (se ano corrente)
            if is_current_year and col == current_month_name:
                col_styles.append('color: #FFA726; font-weight: bold;')
            # Cor da fonte/texto para inativos (ano corrente) ou colorização padrão
            elif not is_active and is_current_year:
                col_styles.append('color: #EF553B')
            else:
                if col == 'Valor Mensal':
                    col_styles.append('color: #00CC96')
                elif col == 'Valor Anual':
                    col_styles.append('color: #3d9df3')
            
            styles.append('; '.join(col_styles))
        return styles

    # Gerar a tabela unificada em HTML
    html_table = []
    html_table.append('<table class="custom-table" style="width: 100%; border-collapse: collapse; border: 1px solid var(--border-color); border-radius: 10px; overflow: hidden; margin-top: 15px; margin-bottom: 15px;">')
    
    # Cabeçalho da tabela
    html_table.append('  <thead>')
    html_table.append('    <tr style="background-color: var(--table-header-bg);">')
    html_table.append('      <th style="padding: 12px 16px; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); text-align: center; border-bottom: 1px solid var(--border-color);">Ativo</th>')
    for mes in meses_ordem:
        html_table.append(f'      <th style="padding: 12px 16px; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); text-align: right; border-bottom: 1px solid var(--border-color);">{mes[:3].upper()}</th>')
    html_table.append('      <th style="padding: 12px 16px; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); text-align: right; border-bottom: 1px solid var(--border-color);">Média</th>')
    html_table.append('      <th style="padding: 12px 16px; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); text-align: right; border-bottom: 1px solid var(--border-color);">Total</th>')
    html_table.append('    </tr>')
    html_table.append('  </thead>')
    
    # Corpo da tabela
    html_table.append('  <tbody>')
    
    now = pd.Timestamp.now()
    is_current_year = (ano == now.year)
    current_month_name = meses_nomes_dict.get(now.month)
    
    # Linhas dos Ativos
    for idx, row in display_df.iterrows():
        orig_ticker = row['OriginalTicker']
        is_active = orig_ticker in active_tickers
        
        row_style = 'background-color: var(--bg-card);'
        ticker_style = 'text-align: center; font-weight: bold; color: var(--text-primary); font-family: monospace;'
        
        if not is_active and is_current_year:
            default_val_color = 'color: #EF553B;'
            ticker_style = 'text-align: center; font-weight: bold; color: #EF553B; font-family: monospace;'
        else:
            default_val_color = 'color: var(--text-primary);'
        
        html_table.append(f'    <tr style="{row_style} transition: background-color 0.2s ease;">')
        html_table.append(f'      <td style="padding: 14px 16px; border-bottom: 1px solid var(--border-color); {ticker_style}">{row["Ativo"]}</td>')
        
        for mes in meses_ordem:
            if is_current_year and mes == current_month_name:
                val_color = 'color: #FFA726; font-weight: bold;'
            else:
                val_color = default_val_color
            html_table.append(f'      <td style="padding: 14px 16px; border-bottom: 1px solid var(--border-color); text-align: right; {val_color}">{row[mes]}</td>')
        
        html_table.append(f'      <td style="padding: 14px 16px; border-bottom: 1px solid var(--border-color); text-align: right; color: #00CC96; font-weight: 500;">{row["Valor Mensal"]}</td>')
        html_table.append(f'      <td style="padding: 14px 16px; border-bottom: 1px solid var(--border-color); text-align: right; color: #3d9df3; font-weight: 500;">{row["Valor Anual"]}</td>')
        html_table.append('    </tr>')
    
    # Linha TOTAL
    total_style = 'background-color: #16181d; font-weight: bold;'
    html_table.append(f'    <tr style="{total_style}">')
    html_table.append('      <td style="padding: 14px 16px; border-bottom: 1px solid var(--border-color); text-align: center; color: var(--text-primary);">TOTAL</td>')
    for col in col_order:
        val_fmt = format_provento(totais_row[col])
        if col == 'Valor Mensal':
            color_total = 'color: #00CC96;'
        elif col == 'Valor Anual':
            color_total = 'color: #3d9df3;'
        else:
            color_total = 'color: var(--text-primary);'
        html_table.append(f'      <td style="padding: 14px 16px; border-bottom: 1px solid var(--border-color); text-align: right; {color_total}">{val_fmt}</td>')
    html_table.append('    </tr>')
    
    ano_mais_antigo = min(anos_disponiveis)
    if ano > ano_mais_antigo:
        # Linha PERCENTUAL DE CRESCIMENTO
        df_prev = proventos_df[proventos_df['ano'] == ano - 1]
        pivot_prev = df_prev.pivot_table(index='ticker', columns='mes', values='valor', aggfunc='sum').fillna(0).rename(columns=meses_nomes_dict)
        for m in meses_ordem:
            if m not in pivot_prev.columns: pivot_prev[m] = 0.0
        totais_prev = pivot_prev[meses_ordem].sum(axis=0)
        tot_prev_full = totais_prev.copy()
        tot_prev_full['Valor Mensal'], tot_prev_full['Valor Anual'] = totais_prev.sum() / 12, totais_prev.sum()
        
        growth_style = 'background-color: #121316;'
        html_table.append(f'    <tr style="{growth_style}">')
        html_table.append('      <td style="padding: 14px 16px; border-bottom: 1px solid var(--border-color); text-align: center; font-size: 0.85rem; font-weight: bold;">📈</td>')
        
        for col in col_order:
            val_curr, val_prev = totais_row[col], tot_prev_full[col]
            if st.session_state.get('hide_values', False):
                val_str = "••••••"
                style_val = 'color: var(--text-secondary); text-align: right;'
            elif val_prev > 0:
                pct = ((val_curr / val_prev) - 1) * 100
                color = "#00CC96" if pct >= 0 else "#EF553B"
                val_str = f"{pct:,.2f}%".replace('.', ',')
                style_val = f'color: {color}; text-align: right; font-weight: bold;'
            else:
                val_str = "0,00%"
                style_val = 'color: var(--text-secondary); text-align: right;'
            
            html_table.append(f'      <td style="padding: 14px 16px; border-bottom: 1px solid var(--border-color); {style_val}">{val_str}</td>')
        html_table.append('    </tr>')
        
        # Linha MÉDIA ACUMULADA
        avg_style = 'background-color: #16181d; font-weight: bold;'
        html_table.append(f'    <tr style="{avg_style}">')
        html_table.append('      <td style="padding: 14px 16px; border-bottom: 1px solid var(--border-color); text-align: center; color: var(--text-primary); font-size: 0.8rem; white-space: nowrap;">MÉDIA ACUMULADA</td>')
        
        mes_limite = now.month if ano == now.year else 12
        for i, m in enumerate(meses_ordem):
            if i < mes_limite:
                media_mes = totais_row[meses_ordem[:i+1]].sum() / (i+1)
                html_table.append(f'      <td style="padding: 14px 16px; border-bottom: 1px solid var(--border-color); text-align: right; color: #00CC96;">{format_provento(media_mes)}</td>')
            else:
                html_table.append('      <td style="padding: 14px 16px; border-bottom: 1px solid var(--border-color);"></td>')
        
        html_table.append('      <td style="padding: 14px 16px; border-bottom: 1px solid var(--border-color);"></td>')
        html_table.append('      <td style="padding: 14px 16px; border-bottom: 1px solid var(--border-color);"></td>')
        html_table.append('    </tr>')
        
    html_table.append('  </tbody>')
    html_table.append('</table>')
    
    st.write('\n'.join(html_table), unsafe_allow_html=True)
    
    # Controles de Adição e Edição
    st.markdown("")
    col_add, col_edit = st.columns([1, 1])
    with col_add:
        if ano == now.year:
            if st.button("➕ Adicionar Ativo", key=f"add_ativo_{ano}", use_container_width=True):
                st.session_state.editing_provento = {'ano': ano, 'ticker': '__NOVO__'}
                st.rerun()
    with col_edit:
        available_tickers = sorted(display_df['OriginalTicker'].unique())
        ticker_options = ["✏️ Selecionar Ativo para Editar/Excluir..."] + [f"{format_ticker_for_display(t)}" for t in available_tickers]
        selected_option = st.selectbox("Editar Ativo", ticker_options, label_visibility="collapsed", key=f"sel_edit_ticker_{ano}")
        if selected_option != "✏️ Selecionar Ativo para Editar/Excluir...":
            sel_idx = ticker_options.index(selected_option) - 1
            original_ticker = available_tickers[sel_idx]
            st.session_state.editing_provento = {'ano': ano, 'ticker': original_ticker}
            st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)
