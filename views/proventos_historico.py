# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import db
import services as svc
from utils.formatters import format_ticker_for_display
from components.ui import render_top_header

def render_proventos_historico_view():
    render_top_header("🗓️ Histórico Mensal", "Detalhamento de proventos recebidos por ativo e ano.")
    
    # --- Bloco de Consulta Status Invest ---
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

        if st.button("🔍 Proventos Futuros", key="btn_statusinvest_consult", use_container_width=True):
            st.session_state.show_statusinvest_results = True

    if st.session_state.get('show_statusinvest_results'):
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
                        st.session_state.show_statusinvest_results = False
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
        selected_mes_nome = st.selectbox("Mês", meses_ordem, key=mes_key)
        if prev_mes_key not in st.session_state: st.session_state[prev_mes_key] = selected_mes_nome
        elif st.session_state[prev_mes_key] != selected_mes_nome:
            st.session_state[val_id_key] += 1
            st.session_state[prev_mes_key] = selected_mes_nome
        selected_mes_num = {v: k for k, v in meses_nomes_dict.items()}[selected_mes_nome]
        current_val = df_prov[(df_prov['ano'] == ano) & (df_prov['ticker'] == ticker) & (df_prov['mes'] == selected_mes_num)]
        default_val = float(current_val['valor'].iloc[0]) if not current_val.empty else 0.0
        dynamic_val_key = f"ve_{ano}_{ticker}_{st.session_state[val_id_key]}"
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
    col_sel, col_empty = st.columns([0.1, 0.9])
    with col_sel:
        ano = st.selectbox("📅 Selecione o Ano", anos_disponiveis, key="sel_ano_detalhe")
    
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
        if not is_active and ano == pd.Timestamp.now().year: return ['color: #EF553B'] * len(row)
        return ['color: #00CC96' if col == 'Valor Mensal' else 'color: #3d9df3' if col == 'Valor Anual' else '' for col in row.index]

    selected = st.dataframe(
        display_df.style.apply(style_row, axis=1).set_properties(**{'text-align': 'right'}, subset=col_order),
        hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row",
        column_config={"OriginalTicker": None}, key=f"prov_df_{ano}_{st.session_state.refresh_id}"
    )
    
    if selected.selection.rows and not st.session_state.get('editing_provento'):
        row_idx = selected.selection.rows[0]
        st.session_state.editing_provento = {'ano': ano, 'ticker': display_df.iloc[row_idx]['OriginalTicker']}
        st.session_state.refresh_id += 1
        st.rerun()

    st.markdown("""
        <style>
        .growth-positive { color: #00CC96 !important; }
        .growth-negative { color: #EF553B !important; }
        th { font-weight: bold !important; font-size: 0.70rem !important; color: #a1a1aa !important; text-transform: uppercase; }
        th:first-child { text-align: center !important; }
        td { font-size: 0.85rem; vertical-align: middle !important; }
        </style>
    """, unsafe_allow_html=True)

    footer_rows = []
    
    # 1. Linha TOTAL
    tm_row = {'MÊS': '<div style="text-align: center; font-size: 0.80rem; font-weight: bold;">TOTAL</div>'}
    for col in col_order:
        val_fmt = format_provento(totais_row[col])
        color = 'color: #00CC96;' if col == 'Valor Mensal' else 'color: #3d9df3;' if col == 'Valor Anual' else ''
        tm_row[col] = f'<div style="text-align: right; font-size: 0.85rem; {color}">{val_fmt}</div>'
    footer_rows.append(tm_row)
    
    ano_mais_antigo = min(anos_disponiveis)
    if ano > ano_mais_antigo:
        # 2. Linha PERCENTUAL DE CRESCIMENTO
        df_prev = proventos_df[proventos_df['ano'] == ano - 1]
        pivot_prev = df_prev.pivot_table(index='ticker', columns='mes', values='valor', aggfunc='sum').fillna(0).rename(columns=meses_nomes_dict)
        for m in meses_ordem:
            if m not in pivot_prev.columns: pivot_prev[m] = 0.0
        totais_prev = pivot_prev[meses_ordem].sum(axis=0)
        tot_prev_full = totais_prev.copy()
        tot_prev_full['Valor Mensal'], tot_prev_full['Valor Anual'] = totais_prev.sum() / 12, totais_prev.sum()
        
        growth_row = {'MÊS': f'<div style="text-align: center; font-size: 0.85rem;">📈</div>'}
        for col in col_order:
            val_curr, val_prev = totais_row[col], tot_prev_full[col]
            if st.session_state.get('hide_values', False):
                growth_row[col] = '<div style="text-align: right; font-size: 0.85rem;">••••••</div>'
            elif val_prev > 0:
                pct = ((val_curr / val_prev) - 1) * 100
                color = "#00CC96" if pct >= 0 else "red"
                growth_row[col] = f'<div style="color: {color}; text-align: right; font-size: 0.85rem;">{pct:,.2f}%</div>'.replace('.', ',')
            else:
                growth_row[col] = '<div style="text-align: right; font-size: 0.85rem;">0,00%</div>'
        footer_rows.append(growth_row)

        # 3. Linha MÉDIA ACUMULADA
        avg_ytd_row = {'MÊS': '<div style="text-align: center; font-size: 0.65rem; color: #a1a1aa; font-weight: bold;">MÉDIA ACUMULADA</div>'}
        mes_limite = pd.Timestamp.now().month if ano == pd.Timestamp.now().year else 12
        for i, m in enumerate(meses_ordem):
            if i < mes_limite:
                media_mes = totais_row[meses_ordem[:i+1]].sum() / (i+1)
                avg_ytd_row[m] = f'<div style="font-size: 0.85rem; text-align: right; color: #00CC96;">{format_provento(media_mes)}</div>'
            else: avg_ytd_row[m] = ''
        avg_ytd_row['Valor Mensal'] = avg_ytd_row['Valor Anual'] = ''
        footer_rows.append(avg_ytd_row)

    df_footer = pd.DataFrame(footer_rows)
    
    # Renomeia colunas para o cabeçalho compacto
    rename_dict = {m: m[:3].upper() for m in meses_ordem}
    rename_dict['Valor Mensal'] = 'MÉDIA'
    rename_dict['Valor Anual'] = 'TOTAL'
    df_footer = df_footer.rename(columns=rename_dict)
    
    st.write(df_footer.to_html(escape=False, index=False), unsafe_allow_html=True)
    if ano == pd.Timestamp.now().year:
        if st.button("➕ Adicionar Ativo", key=f"add_ativo_{ano}"):
            st.session_state.editing_provento = {'ano': ano, 'ticker': '__NOVO__'}
            st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)
