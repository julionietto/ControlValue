import streamlit as st
import base64
import pandas as pd
import yfinance as yf
import database as db
import time
import services as svc
import plotly.express as px
import numpy as np
from streamlit_autorefresh import st_autorefresh
from contextlib import contextmanager
from utils.formatters import format_ticker_for_display, escape_html, format_brl, infer_asset_type, get_annual_proventos_summary
from components.ui import create_card, render_top_header
from components.global_dialogs import dialog_importar_ativos, dialog_importar_proventos, dialog_user_profile
from utils.refresh_manager import is_market_open, get_market_status

import datetime
@st.dialog("Confirmar Exclusão", dismissible=False)
def confirm_delete_dialog(asset_id, ticker):
    st.warning(f"Tem certeza que deseja excluir o ativo **{format_ticker_for_display(ticker)}**?")
    st.write("Esta ação não poderá ser desfeita.")
    
    msg_container = st.empty()
    
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Confirmar Exclusão", type="primary", use_container_width=True):
            loading_html = """
            <div style="background-color: rgba(59, 130, 246, 0.1); border: 1px solid #3b82f6; padding: 1rem; border-radius: 0.5rem; color: #60a5fa; font-weight: 500; display: flex; align-items: center; gap: 0.75rem; animation: pulse 1.5s infinite;">
                <span style="font-size: 1.2rem;">⏳</span> Aguarde... excluindo o ativo do portfólio
            </div>
            <style>
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            </style>
            """
            msg_container.markdown(loading_html, unsafe_allow_html=True)
            time.sleep(1.5)
            db.delete_asset(asset_id, st.session_state.user_id)
            st.session_state.viewing_history = None
            st.session_state.table_key += 1
            st.rerun()
    with col_no:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.show_confirm_delete = False
            st.rerun()

@st.dialog("Confirmar Exclusão de Operação", dismissible=False)
def confirm_delete_operation_dialog(op_data, asset_id):
    st.warning("Tem certeza que deseja excluir esta operação?")
    st.write(f"Data: {op_data['date']} | Quantidade: {op_data['quantity']} | Preço: {op_data['unit_price']}")
    
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Confirmar Exclusão", type="primary", use_container_width=True):
            db.delete_asset_operation(op_data['id'], asset_id, st.session_state.user_id)
            st.session_state.viewing_history = db.get_asset_by_id(asset_id, st.session_state.user_id) # Atualiza dados do ativo no estado
            st.session_state.show_confirm_delete_op = False
            st.success("Operação excluída!")
            st.rerun()
    with col_no:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.show_confirm_delete_op = False
            st.rerun()

@st.dialog("Ativos por Categoria", dismissible=True)
def dialog_assets_by_type(selected_type, assets_df):
    st.markdown(f"### Ativos na Categoria: {selected_type}")
    
    filtered_df = assets_df[assets_df['asset_type'] == selected_type].copy()
    
    if filtered_df.empty:
        st.info("Nenhum ativo encontrado nesta categoria.")
    else:
        display_df = pd.DataFrame()
        display_df['Ticker'] = filtered_df['ticker'].apply(format_ticker_for_display)
        
        def format_qty_hist(qty, a_type):
            if a_type == 'Cripto':
                formatted = f"{qty:,.8f}".replace(",", "X").replace(".", ",").replace("X", ".")
                if "," in formatted: formatted = formatted.rstrip('0').rstrip(',')
                return formatted
            return f"{qty:,.0f}".replace(",", ".")
            
        display_df['Quantidade'] = filtered_df.apply(lambda x: format_qty_hist(x['quantity'], x['asset_type']), axis=1)
        display_df['Saldo Atual'] = filtered_df['current_value'].apply(format_brl)
        
        styled_df = display_df.style.set_properties(**{'text-align': 'center'}, subset=['Ticker', 'Quantidade']) \
                                    .set_properties(**{'text-align': 'right'}, subset=['Saldo Atual']) \
                                    .set_table_styles([dict(selector='th', props=[('text-align', 'center')])])
                                    
        st.dataframe(styled_df, hide_index=True, use_container_width=True)
        
        
    if st.button("Fechar", use_container_width=True):
        st.session_state.pie_dialog_handled = True
        st.rerun()

@st.dialog("Ativos por Setor", dismissible=True)
def dialog_assets_by_sector(selected_sector, assets_df):
    st.markdown(f"<h3 style='text-align: center;'>Ativos no Setor: {selected_sector}</h3>", unsafe_allow_html=True)
    
    filtered_df = assets_df[assets_df['sector'] == selected_sector].copy()
    
    if filtered_df.empty:
        st.info("Nenhum ativo encontrado neste setor.")
    else:
        display_df = pd.DataFrame()
        display_df['Ticker'] = filtered_df['ticker'].apply(format_ticker_for_display)
        
        def format_qty_hist(qty, a_type):
            if a_type == 'Cripto':
                formatted = f"{qty:,.8f}".replace(",", "X").replace(".", ",").replace("X", ".")
                if "," in formatted: formatted = formatted.rstrip('0').rstrip(',')
                return formatted
            return f"{qty:,.0f}".replace(",", ".")
            
        display_df['Quantidade'] = filtered_df.apply(lambda x: format_qty_hist(x['quantity'], x['asset_type']), axis=1)
        display_df['Saldo Atual'] = filtered_df['current_value'].apply(format_brl)
        
        styled_df = display_df.style.set_properties(**{'text-align': 'center'}, subset=['Ticker', 'Quantidade']) \
                                    .set_properties(**{'text-align': 'right'}, subset=['Saldo Atual']) \
                                    .set_table_styles([dict(selector='th', props=[('text-align', 'center')])])
                                    
        st.dataframe(styled_df, hide_index=True, use_container_width=True)
        
    if st.button("Fechar", use_container_width=True):
        st.session_state.sector_dialog_handled = True
        st.rerun()

@st.dialog("FIIs por Classe", dismissible=True)
def dialog_fiis_by_class(selected_class, chart_df):
    st.markdown(f"<h3 style='text-align: center;'>FIIs na Classe: {selected_class}</h3>", unsafe_allow_html=True)
    
    filtered_df = chart_df[chart_df['classe'] == selected_class].copy()
    
    if filtered_df.empty:
        st.info("Nenhum FII encontrado nesta classe.")
    else:
        display_df = pd.DataFrame()
        display_df['Ticker'] = filtered_df['ticker'].apply(format_ticker_for_display)
        
        def format_qty_hist(qty, a_type):
            return f"{qty:,.0f}".replace(",", ".")
            
        display_df['Quantidade'] = filtered_df.apply(lambda x: format_qty_hist(x['quantity'], x['asset_type']), axis=1)
        display_df['Saldo Atual'] = filtered_df['current_value'].apply(format_brl)
        
        styled_df = display_df.style.set_properties(**{'text-align': 'center'}, subset=['Ticker', 'Quantidade']) \
                                    .set_properties(**{'text-align': 'right'}, subset=['Saldo Atual']) \
                                    .set_table_styles([dict(selector='th', props=[('text-align', 'center')])])
                                    
        st.dataframe(styled_df, hide_index=True, use_container_width=True)
        
    if st.button("Fechar", use_container_width=True):
        st.session_state.fii_class_dialog_handled = True
        st.rerun()


@st.dialog("Adicionar novo ativo", dismissible=False)
def dialog_adicionar_novo_ativo():
    categoria = st.radio("Selecione a Categoria", ["Renda Variável", "Renda Fixa"], horizontal=True)
    nome = st.text_input("Nome do Ativo")
    
    # Campo de Moeda (v1.2.1) - Obrigatório para Renda Variável
    moeda_default = 0 # BRL
    if categoria == "Renda Variável" and nome:
        # Tenta inferir para sugerir um default inteligente
        clean_temp = nome.strip().upper()
        if len(clean_temp) >= 4 and "." not in clean_temp and clean_temp not in ['BTC', 'ETH', 'SOL', 'USDT', 'USDC']:
            clean_temp += ".SA"
        tipo_temp = infer_asset_type(clean_temp)
        if tipo_temp in ['Stocks', 'Reits']:
            moeda_default = 1 # USD
            
    moeda = st.selectbox("Moeda de Origem", ["BRL", "USD"], index=moeda_default, help="Selecione a moeda em que você registra suas operações para este ativo.")
    msg_container = st.empty()
    
    if categoria == "Renda Fixa":
        saldo = st.number_input("Saldo Atualizado (R$)", min_value=0.0, format="%.2f")
        st.markdown("")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirmar", type="primary", use_container_width=True):
                if nome:
                    loading_html = """
                    <div style="background-color: rgba(59, 130, 246, 0.1); border: 1px solid #3b82f6; padding: 1rem; border-radius: 0.5rem; color: #60a5fa; font-weight: 500; display: flex; align-items: center; gap: 0.75rem; animation: pulse 1.5s infinite;">
                        <span style="font-size: 1.2rem;">⏳</span> Aguarde... adicionando o novo ativo em seu portfólio
                    </div>
                    <style>
                    @keyframes pulse {
                        0%, 100% { opacity: 1; }
                        50% { opacity: 0.5; }
                    }
                    </style>
                    """
                    msg_container.markdown(loading_html, unsafe_allow_html=True)
                    time.sleep(1.5)
                    db.add_or_update_fixed_income_asset(nome, saldo, st.session_state.user_id)
                    st.success(f"Ativo {nome} adicionado!")
                    st.rerun()
                else:
                    st.error("Informe o nome do ativo.")
        with col2:
            if st.button("Cancelar", use_container_width=True):
                st.rerun()
    else:
        st.info("Ativos brasileiros (Ações/Fiis) recebem o sufixo .SA automaticamente. Para Stocks/Reits/Cripto, digite o ticker completo.")
        st.markdown("")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirmar", type="primary", use_container_width=True):
                if nome:
                    loading_html = """
                    <div style="background-color: rgba(59, 130, 246, 0.1); border: 1px solid #3b82f6; padding: 1rem; border-radius: 0.5rem; color: #60a5fa; font-weight: 500; display: flex; align-items: center; gap: 0.75rem; animation: pulse 1.5s infinite;">
                        <span style="font-size: 1.2rem;">⏳</span> Aguarde... adicionando o novo ativo em seu portfólio
                    </div>
                    <style>
                    @keyframes pulse {
                        0%, 100% { opacity: 1; }
                        50% { opacity: 0.5; }
                    }
                    </style>
                    """
                    msg_container.markdown(loading_html, unsafe_allow_html=True)
                    time.sleep(1.5)
                    clean_name = nome.strip().upper()
                    # Lógica de sufixo .SA (Ações e Fiis)
                    if len(clean_name) >= 4 and "." not in clean_name:
                        # Se não for Cripto conhecido sem hífen
                        if clean_name not in ['BTC', 'ETH', 'SOL', 'USDT', 'USDC']:
                            clean_name += ".SA"
                    
                    tipo_inicial = infer_asset_type(clean_name)
                    # Se for renda variável, valida a cotação ANTES de inserir no BD
                    live_native = 0.0
                    live_brl = 0.0
                    if tipo_inicial != 'Renda Fixa':
                        ticker_to_fetch = clean_name
                        if tipo_inicial == 'Cripto' and '-' not in clean_name:
                            ticker_to_fetch = f"{clean_name}-USD"
                            
                        try:
                            prices = svc.fetch_current_prices([ticker_to_fetch], st.session_state.refresh_id)
                            live_native = prices.get(ticker_to_fetch, 0.0)
                            
                            if tipo_inicial in ['Cripto', 'Stocks', 'Reits']:
                                cot = svc.get_usd_brl_rate(st.session_state.refresh_id)
                                live_brl = live_native * cot if cot > 0 else 0.0
                            else:
                                live_brl = live_native
                        except Exception as e:
                            import logging
                            logging.warning(f"Aviso ao buscar preço de {ticker_to_fetch}: {e}")
                        
                        if live_native <= 0.0:
                            msg_container.empty()
                            st.error(f"É possível que o ativo informado ('{clean_name}') não exista. Por favor, digite o código do ativo novamente.")
                            st.stop()
                            
                    # Adiciona ou recupera o ativo
                    db.add_empty_asset(clean_name, tipo_inicial, st.session_state.user_id, currency=moeda)
                    
                    # Busca os dados carregados do BD para garantir consistência
                    with db.get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT * FROM assets WHERE ticker = %s AND user_id = %s", (clean_name, st.session_state.user_id))
                        row = cursor.fetchone()
                        if row:
                            asset_data = {
                                'id': row[0],
                                'ticker': row[1],
                                'asset_type': row[2],
                                'quantity': row[3],
                                'average_price': row[4],
                                'price_ceiling': row[5],
                                'fair_value': row[6],
                                'currency': row[8]
                            }
                            
                            if tipo_inicial != 'Renda Fixa':
                                asset_data['original_current_price'] = live_native
                                asset_data['current_price'] = live_brl

                            st.session_state.viewing_history = asset_data
                            st.session_state.navigation_tab = "Detalhe do Ativo"
                            st.session_state.scroll_to_top = True
                            st.rerun()
                else:
                    st.error("Informe o nome do ativo.")
        with col2:
            if st.button("Cancelar", use_container_width=True):
                st.rerun()


# Lógica de detalhes migrada para views/asset_detail.py

# Inicializa o banco de dados

def render_visao_geral_view():
    # HEADER INTERNALIZED - This forces a native scroll reset on navigation
    render_top_header("Ativos Financeiros", "Controle de investimentos e análise de performance em tempo real.")

    # Renderiza Visão Geral

    assets_df = db.get_all_assets(st.session_state.user_id)
    if assets_df.empty:
        st.info("O seu portfólio está vazio no momento. Comece adicionando o seu primeiro ativo!")
        if st.button("Adicionar novo ativo", type="primary", key="btn_add_first_asset"):
            dialog_adicionar_novo_ativo()
    else:
        # Buscar preços atualizados
        # Para Renda Fixa, MVP: usamos o preço médio como valor atual (sem flutuação de mercado via YF)
        tickers_to_fetch = assets_df[assets_df['asset_type'] != 'Renda Fixa']['ticker'].unique().tolist()
        
        # Mapeamento de tickers para busca no Yahoo Finance
        ticker_fetch_map = {}
        tickers_br = []
        tickers_us = []
        tickers_crypto = []

        for t in tickers_to_fetch:
            asset_r = assets_df[assets_df['ticker'] == t].iloc[0]
            a_type = asset_r['asset_type']
            
            if a_type == 'Cripto':
                yf_t = f"{t}-USD" if '-' not in t else t
                ticker_fetch_map[t] = yf_t
                tickers_crypto.append(yf_t)
            elif a_type in ['Stocks', 'Reits']:
                ticker_fetch_map[t] = t
                tickers_us.append(t)
            else: # Ações e Fiis
                ticker_fetch_map[t] = t
                tickers_br.append(t)
    
        # Determina quais tickers realmente buscar com base nas regras de mercado
        m_status = get_market_status()
        is_first_load = st.session_state.get('is_first_load', True)
        
        # Inicializa cache de preços no session_state se não existir
        if 'price_cache' not in st.session_state:
            st.session_state.price_cache = {}

        # Prepara dados e verifica se é Auto-Refresh
        current_datarefresh = st.session_state.get('datarefresh', 0)
        is_auto_refresh = False
        if 'last_datarefresh' not in st.session_state:
            st.session_state.last_datarefresh = current_datarefresh
            is_auto_refresh = True
        elif current_datarefresh != st.session_state.last_datarefresh:
            st.session_state.last_datarefresh = current_datarefresh
            is_auto_refresh = True

        final_tickers_to_fetch = []
        for t in tickers_br:
            if (m_status['BR'] and is_auto_refresh) or is_first_load or t not in st.session_state.price_cache:
                final_tickers_to_fetch.append(t)
        
        for t in tickers_us:
            if (m_status['US'] and is_auto_refresh) or is_first_load or t not in st.session_state.price_cache:
                final_tickers_to_fetch.append(t)
                
        for t in tickers_crypto:
            if (m_status['CRYPTO'] and is_auto_refresh) or t not in st.session_state.price_cache: # Bitcoin sempre entra
                final_tickers_to_fetch.append(t)

        with st.spinner("Buscando preços atualizados..."):
            refresh_id = st.session_state.refresh_id
            
            # Só chama a API para o que o mercado permitir (ou se for a primeira carga ou ativo novo)
            if final_tickers_to_fetch:
                new_prices = svc.fetch_current_prices(final_tickers_to_fetch, refresh_id)
                st.session_state.price_cache.update(new_prices)
            
            # O current_prices final é a união do que acabamos de buscar com o que já tínhamos no cache
            current_prices = st.session_state.price_cache
                
            assets_tuple = (tuple(assets_df['ticker'].tolist()), tuple(assets_df['asset_type'].tolist()))
            sectors_dict = svc.fetch_asset_sectors(assets_tuple, is_auto_refresh)
            
            usd_to_brl_rate = svc.get_usd_brl_rate(refresh_id, is_first_load)
            btc_to_usd_rate = svc.get_btc_usd_rate(refresh_id)
            ibov_points = svc.get_ibov(refresh_id, is_first_load)
            
            # Após a carga inicial de todos os dados e indicadores, desmarca a flag
            st.session_state.is_first_load = False
            
        # Alerta de Mercados Fechados
        closed_markets = []
        if not m_status['BR'] and (tickers_br or assets_df[assets_df['asset_type'] == 'Renda Fixa'].empty == False):
            closed_markets.append("Brasil (B3)")
        if not m_status['US'] and tickers_us:
            closed_markets.append("EUA (NYSE/NASDAQ)")
            
        if closed_markets:
            st.info(f"ℹ️ **Auto-refresh pausado:** {', '.join(closed_markets)} - Mercado Fechado no momento.", icon="🕒")

        st.markdown("### 🏛️ Indicadores de Mercado")
        col_ind1, col_ind2, col_ind3 = st.columns(3)
        with col_ind1: create_card("Dólar (USD/BRL)", format_brl(usd_to_brl_rate))
        
        # Formatação BTC com padrão BRL: Ponto para milhares, vírgula para decimais
        btc_formatted = f"US$ {btc_to_usd_rate:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        with col_ind2: create_card("Bitcoin (BTC/USD)", btc_formatted)
        
        with col_ind3: create_card("IBOVESPA", f"{ibov_points:,.0f} pts".replace(",", "."))
            
        st.markdown("---")
        
        # Função para determinar o preco atual na tabela original
        def get_current_price(row):
            if row['asset_type'] == 'Renda Fixa':
                return row['average_price']  # MVP Renda Fixa (não sofre variação em tempo real via yahoo)
            
            # Usa o mapeamento para pegar o preço correto do dicionário
            ticker = row['ticker']
            yf_ticker = ticker_fetch_map.get(ticker, ticker)
            return current_prices.get(yf_ticker, 0.0)
    
        # Função para converter valores em USD para BRL
        foreign_input_types = ['Stocks', 'Reits'] # Cripto é BRL por padrão no input (preço médio)
        foreign_market_types = ['Cripto', 'Stocks', 'Reits'] # Cripto vem do YF em USD (BTC-USD)
        
        def apply_exchange_rate(row, column_name, is_market_price=False):
            val = row[column_name]
            # Usa agora o campo explícito 'currency' (v1.2.1)
            # is_market_price refere-se à cotação vinda do YF
            # Para Stocks/Reits/Cripto, o YF sempre retorna em USD ou moeda nativa internacional (que tratamos como USD no MVP)
            if row['currency'] == 'USD' or (is_market_price and row['asset_type'] in ['Cripto', 'Stocks', 'Reits']):
                # Se o registro é em BRL mas o mercado é USD (Cripto), converte mercado para BRL
                # Se o registro é em USD, converte o valor final para BRL para o Dashboard
                return val * usd_to_brl_rate
            return val
    
        # Adiciona os preços diretos da fonte (em suas moedas originais da busca)
        assets_df['original_current_price'] = assets_df.apply(get_current_price, axis=1)
        
        # Aplica a conversão para BRL onde for necessário (transformando as métricas base para Reais)
        assets_df['average_price_brl'] = assets_df.apply(lambda row: apply_exchange_rate(row, 'average_price', is_market_price=False), axis=1)
        assets_df['current_price'] = assets_df.apply(lambda row: apply_exchange_rate(row, 'original_current_price', is_market_price=True), axis=1)
        
        # Mapeia Setores
        assets_df['sector'] = assets_df['ticker'].map(sectors_dict)
        
        # Recalcula totais usando EXCLUSIVAMENTE variáveis convertidas em BRL
        assets_df['total_invested'] = assets_df['quantity'] * assets_df['average_price_brl']
        assets_df['current_value'] = assets_df['quantity'] * assets_df['current_price']
        
        # Otimização: Busca TODOS os históricos de ações em um ÚNICO Round-Trip para combater o N+1
        all_histories_df = db.get_all_asset_histories(st.session_state.user_id)
        
        def calculate_asset_totals(row):
            base_invested = row['quantity'] * row['average_price_brl']
            base_profit = row['current_value'] - base_invested
            
            if row['asset_type'] == 'Renda Fixa':
                return pd.Series({'profit_loss': 0.0, 'total_invested': base_invested})
                
            if not all_histories_df.empty:
                history_df = all_histories_df[all_histories_df['asset_id'] == row['id']].copy()
            else:
                history_df = pd.DataFrame()
            
            if history_df.empty:
                return pd.Series({'profit_loss': base_profit, 'total_invested': base_invested})
                
            def convert_to_brl(val):
                if row['currency'] == 'USD':
                    return val * usd_to_brl_rate
                return val
    
            history_df['unit_price_brl'] = history_df['unit_price'].apply(convert_to_brl)
            history_df['valor_operacao'] = history_df['quantity'] * history_df['unit_price_brl']
            history_df['valor_atualizado'] = history_df['quantity'] * row['current_price']
            history_df['lucro_prejuizo'] = history_df['valor_atualizado'] - history_df['valor_operacao']
            
            return pd.Series({
                'profit_loss': history_df['lucro_prejuizo'].sum(),
                'total_invested': history_df['valor_operacao'].sum()
            })
    
        totals_df = assets_df.apply(calculate_asset_totals, axis=1)
        assets_df['profit_loss'] = totals_df['profit_loss']
        assets_df['total_invested'] = totals_df['total_invested']
        assets_df['profit_loss_pct'] = (assets_df['profit_loss'] / assets_df['total_invested']) * 100
    
        # Resumo Geral
        total_invested = assets_df['total_invested'].sum()
        current_total_value = assets_df['current_value'].sum()
        
        # Busca Alocações de Meta do Usuário para o Balanceamento
        user_targets = db.get_user_allocations(st.session_state.user_id)
        
        # Calcula Percentuais Atuais por Classe para validar "Melhor Compra"
        current_allocs_pct = {}
        if current_total_value > 0:
            current_allocs_pct['Ações'] = (assets_df[assets_df['asset_type'].isin(['Ações', 'ETF'])]['current_value'].sum() / current_total_value) * 100
            current_allocs_pct['Fiis'] = (assets_df[assets_df['asset_type'] == 'Fiis']['current_value'].sum() / current_total_value) * 100
            current_allocs_pct['Criptos'] = (assets_df[assets_df['asset_type'] == 'Cripto']['current_value'].sum() / current_total_value) * 100
            current_allocs_pct['Renda Fixa'] = (assets_df[assets_df['asset_type'] == 'Renda Fixa']['current_value'].sum() / current_total_value) * 100
            current_allocs_pct['Ativos Internacionais'] = (assets_df[assets_df['asset_type'].isin(['Stocks', 'Reits'])]['current_value'].sum() / current_total_value) * 100
        else:
            current_allocs_pct = {k: 0.0 for k in user_targets.keys()}
        
        # Salva no session_state para que outros componentes (diálogos) possam acessar sem recalcular
        st.session_state.current_allocs_pct = current_allocs_pct
        
        # Busca todos os proventos globais
        global_total_proventos = db.get_all_total_proventos(st.session_state.user_id)
        
        # Retorno Total = Lucro/Prejuízo + Proventos Globais
        total_profit_loss = assets_df['profit_loss'].sum() + global_total_proventos
        total_profit_loss_pct = (total_profit_loss / total_invested * 100) if total_invested > 0 else 0
        
        total_renda_fixa = assets_df[assets_df['asset_type'] == 'Renda Fixa']['current_value'].sum()
        total_renda_variavel = assets_df[assets_df['asset_type'] != 'Renda Fixa']['current_value'].sum()
        
        # Calcular o total de ações/FIIs/Reits/Stocks/ETFs (ignora Cripto e Renda Fixa)
        tipos_acoes = ['Ações', 'Fiis', 'ETF', 'Stocks', 'Reits']
        total_qtd_acoes = assets_df[assets_df['asset_type'].isin(tipos_acoes)]['quantity'].sum()
    
        st.markdown("### 💰 Valores Sumarizados")
        
        # Primeira linha com 4 colunas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1: create_card("Total Investido", format_brl(total_invested))
        
        # Saldo Atual não tem mais percentual delta (conforme user anterior, ou mantemos?)
        # O user pediu para acrescentar percentual no Retorno Total.
        with col2: create_card("Saldo Atual", format_brl(current_total_value))
        
        with col3: create_card("Total de Proventos", format_brl(global_total_proventos))
        
        profit_pct_formatted = f"{total_profit_loss_pct:,.2f}%".replace(".", ",")
        with col4: create_card("Retorno Total", format_brl(total_profit_loss), profit_pct_formatted)
        
        # Segunda linha com 3 colunas para os totais de Renda Fixa, Variável e Qtd de Ações
        col5, col6, col7 = st.columns(3)
        
        with col5: create_card("Total Renda Fixa", format_brl(total_renda_fixa))
        with col6: create_card("Total Renda Variável", format_brl(total_renda_variavel))
        
        # Qtd. formatada com ponto de milhares e sem decimais
        qtd_formatted = f"{total_qtd_acoes:,.0f}".replace(",", ".")
        with col7: create_card("Quantidade de Ações/Fiis", qtd_formatted)
    
        st.markdown("---")
    
        # Calcula o peso de cada ativo em relação ao saldo total
        assets_df['weight_pct'] = (assets_df['current_value'] / current_total_value) * 100 if current_total_value > 0 else 0
        assets_df['orientation'] = "Em construção"
    
        # Exibindo os dados de forma tabular
        st.markdown('<h3 style="text-align: center; color: #ffffff; margin-bottom: -1.5rem;">Meus Ativos</h3>', unsafe_allow_html=True)
        
        display_df = assets_df[['id', 'ticker', 'asset_type', 'quantity', 'average_price_brl', 'current_price', 'current_value', 'weight_pct', 'orientation']].copy()
        display_df.columns = ['ID', 'Ticker', 'Tipo', 'Qtd', 'Preço Médio', 'Preço Atual', 'Valor Atual', 'Peso %', 'Orientação']
        
        # Formata como strings direto no dataframe para o st.dataframe permitir sort (ordenação) nativamente
        display_df['Preço Médio'] = display_df['Preço Médio'].apply(format_brl)
        display_df['Preço Atual'] = display_df['Preço Atual'].apply(format_brl)
        display_df['Valor Atual'] = display_df['Valor Atual'].apply(format_brl)
        display_df['Peso %'] = display_df['Peso %'].apply(lambda x: f"{x:,.2f}%".replace(".", ","))
        
        # Quantidade formata 8 casas decimais para Cripto, 0 para o resto (como texto)
        def format_qty(row):
            if row['Tipo'] == 'Cripto':
                return f"{row['Qtd']:.8f}".rstrip('0').rstrip('.')
            return f"{row['Qtd']:.0f}"
        
        display_df['Qtd'] = display_df.apply(format_qty, axis=1)
        
        # Substitui os valores irrelevantes para Renda Fixa por 'N/A'
        is_rf = display_df['Tipo'] == 'Renda Fixa'
        cols_to_na = ['Qtd', 'Preço Médio', 'Preço Atual']
        for col in cols_to_na:
            display_df.loc[is_rf, col] = 'N/A'
            
        # Especificamente para BTC-USD, não mais oculta preços
        # logic removed as per user request
    
    
        def format_brl_custom(val, is_currency=True):
            if pd.isna(val) or val == 0: 
                return "R$ 0,00" if is_currency else "0,00"
            formatted = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"R$ {formatted}" if is_currency else formatted
    
        def format_qty_table(row):
            if row['asset_type'] == 'Cripto':
                # Formata com até 8 casas, usando padrão BRL (ponto milhar, vírgula decimal)
                formatted = f"{row['quantity']:,.8f}".replace(",", "X").replace(".", ",").replace("X", ".")
                # Remove zeros à direita e a vírgula se ficar isolada
                if "," in formatted:
                    formatted = formatted.rstrip('0').rstrip(',')
                return formatted
            return f"{row['quantity']:,.0f}".replace(",", ".")
    
        # --- TABELA DE ATIVOS: UNIFICADA COM OPERAÇÕES INDIVIDUAIS PARA CRIPTO ---
        
        all_rows = []
        
        for _, asset in assets_df.iterrows():
            # Para todos os ativos, usamos a linha consolidada original do assets_df
            val_op = asset['total_invested']
            val_at = asset['current_value']
            
            # Lógica de Orientação
            if asset['asset_type'] == 'Renda Fixa':
                orientation = "COMPRA"
            else:
                price_ceiling = asset.get('price_ceiling', 0)
                current_price_orig = asset['original_current_price']
                orientation = "COMPRA" if current_price_orig <= price_ceiling else "AGUARDE"
            
            all_rows.append({
                'id': asset['id'],
                'ticker': asset['ticker'],
                'Tipo': asset['asset_type'],
                'Quantidade': asset['quantity'],
                'Preço': asset['average_price_brl'],
                'Valor da operação': val_op,
                'Cotação Atual': current_price_orig,
                'Valor atualizado': val_at,
                'Orientação': orientation,
                'Lucro / Prejuízo': asset['profit_loss'],
                'Peso %': asset['weight_pct'],
                'currency': asset['currency']
            })
        
        unified_df = pd.DataFrame(all_rows)
        if not unified_df.empty:
            unified_df = unified_df.sort_values(by='ticker', ascending=True).reset_index(drop=True)
        
        # Formatação para exibição
        display_unified = unified_df.copy()
        display_unified['ticker'] = display_unified['ticker'].apply(format_ticker_for_display)
        
        # Função de formatação de quantidade (8 casas para Cripto, 0 para outros)
        def format_qty_unified(row):
            if row['Tipo'] == 'Cripto':
                formatted = f"{row['Quantidade']:,.8f}".replace(",", "X").replace(".", ",").replace("X", ".")
                if "," in formatted:
                    formatted = formatted.rstrip('0').rstrip(',')
                return formatted
            if row['Tipo'] == 'Renda Fixa':
                return 'N/A'
            return f"{row['Quantidade']:,.0f}".replace(",", ".")
    
        display_unified['Qtd'] = display_unified.apply(format_qty_unified, axis=1)
        
        def format_usage_currency(row):
            val = row['Cotação Atual']
            if row['currency'] == 'USD':
                return f"$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            elif row['Tipo'] == 'Renda Fixa':
                return 'N/A'
            else:
                return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
        display_unified['Cotação Atual Display'] = display_unified.apply(format_usage_currency, axis=1)
        display_unified['Preço Unit.'] = display_unified['Preço'].apply(format_brl_custom)
        display_unified['Vlr. Operação'] = display_unified['Valor da operação'].apply(format_brl_custom)
        display_unified['Vlr. Atualizado'] = display_unified['Valor atualizado'].apply(format_brl_custom)
        display_unified['Peso %'] = display_unified['Peso %'].apply(lambda x: f"{x:,.2f}%".replace(".", ","))
        
        final_cols = ['ticker', 'Tipo', 'Qtd', 'Cotação Atual Display', 'Vlr. Atualizado', 'Orientação', 'Peso %']
        final_df = display_unified[final_cols]
        final_df.columns = ['Ativo', 'Tipo', 'Quantidade', 'Cotação Atual', 'Valor atualizado', 'Orientação', 'Peso %']
        
        # Estilização da coluna Orientação
        def style_orientation_cells(val):
            if val == "COMPRA":
                return 'background-color: #00CC96; color: white; font-weight: bold; text-align: center;'
            elif val == "AGUARDE":
                return 'background-color: #EF553B; color: white; font-weight: bold; text-align: center;'
            return ''
    
        styled_final_df = final_df.style.map(style_orientation_cells, subset=['Orientação'])
        
        # Alinhamentos via Style
        styled_final_df = styled_final_df.set_properties(**{'text-align': 'center'}, subset=['Ativo', 'Tipo', 'Quantidade', 'Orientação']) \
                                         .set_properties(**{'text-align': 'right'}, subset=['Cotação Atual', 'Valor atualizado', 'Peso %']) \
                                         .set_table_styles([dict(selector='th', props=[('text-align', 'center')])])
        
        st.markdown('<div style="font-size: 0.85rem; color: #a1a1aa; margin-bottom: 5px; margin-left: 2px;">✏️</div>', unsafe_allow_html=True)
        selected = st.dataframe(
            styled_final_df,
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            key=f"unified_df_{st.session_state.table_key}"
        )
        
        if selected.selection.rows:
            row_idx = selected.selection.rows[0]
            ticker_to_edit = final_df.iloc[row_idx]['Ativo']
            # Precisamos achar o ID original no unified_df
            asset_id = unified_df.iloc[row_idx]['id']
            asset_data = assets_df[assets_df['id'] == asset_id].iloc[0]
            st.session_state.viewing_history = asset_data.to_dict()
            st.session_state.navigation_tab = "Detalhe do Ativo"
            st.session_state.scroll_to_top = True
            st.rerun()
    
        # Botão Adicionar novo ativo
        st.markdown("")
        if st.button("Adicionar novo ativo", type="primary", use_container_width=False):
            dialog_adicionar_novo_ativo()
    
        st.markdown("---")
    
        # --- SEÇÃO RADAR ---
        st.markdown('<h2 style="text-align: center; color: #ffffff; margin-top: 0.5rem; margin-bottom: 1.5rem;">Balanceamento e Diversificação</h2>', unsafe_allow_html=True)
    
        # Mapeamento do asset_type para a chave de user_targets
        def get_target_class_key(a_type):
            if a_type in ['Ações', 'ETF']: return 'Ações'
            if a_type == 'Fiis': return 'Fiis'
            if a_type == 'Cripto': return 'Criptos'
            if a_type == 'Renda Fixa': return 'Renda Fixa'
            if a_type in ['Stocks', 'Reits']: return 'Ativos Internacionais'
            return None

        # Elegível se: 
        # 1. Preço atual < Preço Teto
        # 2. A classe do ativo está ABAIXO da meta de alocação (%)
        def is_eligible(row):
            if row['original_current_price'] >= row['price_ceiling']:
                return False
            
            target_key = get_target_class_key(row['asset_type'])
            if target_key:
                target_pct = user_targets.get(target_key, 0.0)
                current_pct = current_allocs_pct.get(target_key, 0.0)
                return current_pct < target_pct
            return False
            
        any_eligible = False
        full_radar_df = assets_df[assets_df['asset_type'].isin(['Ações', 'Fiis', 'ETF', 'Stocks', 'Reits'])].copy()
        if not full_radar_df.empty:
            full_radar_df['eligible'] = full_radar_df.apply(is_eligible, axis=1)
            any_eligible = full_radar_df['eligible'].any()
            
        if not any_eligible and not full_radar_df.empty:
            st.warning("Considere aportar em Renda Fixa ou revise os percentuais de alocação na opção de Alocação de Ativos")

        def show_radar_table(title, asset_types, df, user_targets, current_allocs_pct):
            st.markdown(f"<h3 style='text-align: center; color: #ffffff; font-size: 1.2rem; margin-bottom: 1rem;'>{title}</h3>", unsafe_allow_html=True)
            radar_df = df[df['asset_type'].isin(asset_types)].copy()
            
            if not radar_df.empty:
                # Ordena por valor total do ativo na carteira de forma crescente
                radar_df = radar_df.sort_values(by='current_value', ascending=True)
                
                # Regra de Indicação de Compra
                radar_df['Indicação de Compra'] = "Aguardar"

                radar_df['eligible'] = radar_df.apply(is_eligible, axis=1)
                
                if radar_df['eligible'].any():
                    # Como já está ordenado pelo menor Valor do Ativo (current_value), o primeiro elegível é o vencedor
                    best_buy_idx = radar_df[radar_df['eligible']].index[0]
                    radar_df.loc[best_buy_idx, 'Indicação de Compra'] = "Melhor Compra"
                
                # Prepara o dataframe de exibição
                display_radar = pd.DataFrame()
                display_radar['Ticker'] = radar_df['ticker'].apply(format_ticker_for_display)
                display_radar['Valor do Ativo'] = radar_df['current_value'].apply(format_brl_custom)
                display_radar['Indicação de Compra'] = radar_df['Indicação de Compra']
                
                # Estilização
                def style_indication(val):
                    if val == "Melhor Compra":
                        return 'color: #00CC96; font-weight: bold; text-align: center;'
                    return 'color: #a1a1aa; text-align: center;'
                
                styled_radar = display_radar.style.map(style_indication, subset=['Indicação de Compra']) \
                                                 .set_properties(**{'text-align': 'center'}, subset=['Ticker']) \
                                                 .set_properties(**{'text-align': 'right'}, subset=['Valor do Ativo'])
                
                st.dataframe(
                    styled_radar, 
                    hide_index=True, 
                    use_container_width=True
                )
            else:
                st.info(f"Nenhum ativo do tipo {', '.join(asset_types)} para exibir no {title}.")
    
        has_us_assets = not assets_df[assets_df['asset_type'].isin(['Stocks', 'Reits'])].empty
    
        if has_us_assets:
            col_radar1, col_radar2 = st.columns(2)
            with col_radar1:
                show_radar_table("Ativos no Brasil", ['Ações', 'Fiis', 'ETF'], assets_df, user_targets, current_allocs_pct)
            with col_radar2:
                show_radar_table("Ativos nos Estados Unidos", ['Stocks', 'Reits'], assets_df, user_targets, current_allocs_pct)
        else:
            show_radar_table("Ativos no Brasil", ['Ações', 'Fiis', 'ETF'], assets_df, user_targets, current_allocs_pct)
    
    
        # Gráficos
        st.markdown("---")
        st.markdown('<h2 style="color: #ffffff; font-size: 1.5rem; margin-bottom: 1.5rem;">Análise de Gráficos</h2>', unsafe_allow_html=True)
        
        # Verifica se há opções para exibir a aba de Dividendos Sintéticos
        has_options_data = not db.get_opcoes(st.session_state.user_id).empty
    
        tabs_labels = ["Distribuição do Portfólio", "Distribuição por Setores"]
        if has_us_assets:
            tabs_labels.append("Ativos EUA")
        tabs_labels.extend(["Fundos Imobiliários (FII)", "Renda Passiva"])
        if has_options_data:
            tabs_labels.append("Dividendos Sintéticos")
        
        tabs = st.tabs(tabs_labels)
        tab_dist = tabs[0]
        tab_setores = tabs[1]
        
        idx = 2
        if has_us_assets:
            tab_us = tabs[idx]
            idx += 1
        else:
            tab_us = None
            
        tab_fii = tabs[idx]; idx += 1
        tab_passiva = tabs[idx]; idx += 1
        
        if has_options_data:
            tab_sinteticos = tabs[idx]
            idx += 1
        else:
            tab_sinteticos = None
        
        with tab_dist:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                if current_total_value > 0:
                    # O Plotly/Streamlit não emite eventos on_select para gráficos de pizza.
                    # Utilizando um gráfico de barras horizontais (Treemap/Bar) para suportar a interatividade
                    bar_df = assets_df.groupby('asset_type', as_index=False)['current_value'].sum()
                    bar_df = bar_df.sort_values('current_value', ascending=True)
                    
                    bar_df['percentual'] = (bar_df['current_value'] / current_total_value) * 100
                    bar_df['text_pct'] = bar_df['percentual'].apply(lambda x: f"{x:.2f}%".replace('.', ','))
                    
                    fig_type = px.bar(
                        bar_df, 
                        x='current_value', 
                        y='asset_type', 
                        orientation='h', 
                        title='Por Classe de Ativo', 
                        color='asset_type',
                        text='text_pct'
                    )
                    fig_type.update_layout(
                        clickmode='event+select', 
                        showlegend=False,
                        xaxis_title="Saldo Total (R$)",
                        yaxis_title=""
                    )
                    event = st.plotly_chart(fig_type, use_container_width=True, on_select="rerun", key="pie_chart_type")
                    
                    if event and event.selection and event.selection.points:
                        selected_type = event.selection.points[0].get("y", "") # No gráfico de barras horizontal, a categoria fica no eixo Y
                        
                        if selected_type and st.session_state.get('last_pie_selection') != selected_type:
                            st.session_state.pie_dialog_handled = False
                            st.session_state.last_pie_selection = selected_type
                            
                        if not st.session_state.get('pie_dialog_handled'):
                            dialog_assets_by_type(selected_type, assets_df)
                else:
                    st.write("Sem valor suficiente para gráfico.")
                
            with col_g2:
                if current_total_value > 0:
                    plot_df = assets_df.copy()
                    plot_df['ticker_display'] = plot_df['ticker'].apply(format_ticker_for_display)
                    fig_asset = px.pie(plot_df, values='current_value', names='ticker_display', title='Por Ativo Específico', hole=0.4)
                    st.plotly_chart(fig_asset, use_container_width=True)
                else:
                    st.write("Sem valor suficiente para gráfico.")
            
            # --- NOVO GRÁFICO: Performance do Portfólio ---
            st.markdown("---")
            st.subheader("📊 Rentabilidade do Portfólio vs Índices (Últimos 12 Meses)")
            use_cached_perf = ('perf_v5' in st.session_state and st.session_state.perf_v5.get('user_id') == st.session_state.user_id)
            if use_cached_perf:
                perf_df = st.session_state.perf_v5['perf_df']
                all_assets_user_empty = perf_df.empty
            else:

                with st.spinner("Calculando rentabilidade histórica..."):
                    # 1. Buscar Histórico de Índices
                    indices = svc.get_major_indices_history(months=12)

                    # 2. Reconstruir Histórico do Portfólio
                    # Precisamos dos tickers que compuseram o portfólio nos últimos 12 meses
                    all_assets_user = db.get_all_assets(st.session_state.user_id)
                    if not all_assets_user.empty:
                        # Obter datas dos últimos 12 meses (fim de cada mês)
                        # 2. Calcular histórico do portfólio
                        hoje = pd.Timestamp.now().normalize()
                        meses_fechamento = []
                        for i in range(12, 0, -1):
                            d = hoje - pd.DateOffset(months=i)
                            last_day = d + pd.offsets.MonthEnd(0)
                            meses_fechamento.append(last_day.normalize())

                        # Buscar histórico de preços para todos os tickers
                        tickers_port = all_assets_user['ticker'].unique().tolist()

                        # Fetch historical prices in BULK
                        price_history = {}
                        tickers_for_yf = []
                        for t in tickers_port:
                            asset_row = all_assets_user[all_assets_user['ticker']==t]
                            if not asset_row.empty:
                                if asset_row['asset_type'].iloc[0] == 'Renda Fixa':
                                    continue
                                tyf = f"{t}-USD" if (asset_row['asset_type'].iloc[0]=='Cripto' and '-' not in t) else t
                                if tyf not in tickers_for_yf:
                                    tickers_for_yf.append(tyf)

                        if "BRL=X" not in tickers_for_yf:
                            tickers_for_yf.append("BRL=X")

                        if tickers_for_yf:
                            hist_data = yf.download(tickers_for_yf, period="2y", threads=True, progress=False, ignore_tz=True)
                            if not hist_data.empty and 'Close' in hist_data.columns:
                                close_df = hist_data['Close']
                                if len(tickers_for_yf) == 1:
                                    t = tickers_for_yf[0]
                                    price_history[t] = close_df.dropna()
                                else:
                                    for t in tickers_for_yf:
                                        if t in close_df.columns:
                                            price_history[t] = close_df[t].dropna()

                        for key, hist in price_history.items():
                            if not hist.empty:
                                if hist.index.tz is not None:
                                    hist.index = hist.index.tz_localize(None)
                                hist.index = hist.index.normalize()
                                price_history[key] = hist

                        usd_rate_hist = price_history.get("BRL=X", pd.Series())

                        # Calcular valor do portfólio em cada fechamento de mês
                        portfolio_values = []
                        for dt in meses_fechamento:
                            total_dt = 0.0
                            for _, asset in all_assets_user.iterrows():
                                # Uso direto da DF all_histories_df para eliminar consultas SQL no banco
                                if not all_histories_df.empty:
                                    history_asset = all_histories_df[all_histories_df['asset_id'] == asset['id']].copy()
                                else:
                                    history_asset = pd.DataFrame()

                                if not history_asset.empty:
                                    history_asset['date'] = pd.to_datetime(history_asset['date'], format='mixed', dayfirst=False).dt.normalize()
                                    qty_at_dt = history_asset[history_asset['date'] <= dt]['quantity'].sum()

                                    if qty_at_dt > 0:
                                        # Preço na data dt (ou o mais próximo anterior)
                                        t = asset['ticker']
                                        tyf = t + "-USD" if (asset['asset_type']=='Cripto' and '-' not in t) else t
                                        if tyf in price_history:
                                            p_hist = price_history[tyf]
                                            available_dates = p_hist.index[p_hist.index <= dt]
                                            if not available_dates.empty:
                                                p = p_hist.loc[available_dates[-1]]
                                                if isinstance(p, pd.Series): p = p.iloc[0]
                                                p = float(p)

                                                # Conversão se necessário
                                                if asset['asset_type'] in ['Stocks', 'Reits', 'Cripto']:
                                                    u_dates = usd_rate_hist.index[usd_rate_hist.index <= dt]
                                                    rate = usd_rate_hist.loc[u_dates[-1]] if not u_dates.empty else usd_to_brl_rate
                                                    if isinstance(rate, pd.Series): rate = rate.iloc[0]
                                                    rate = float(rate)
                                                    p = p * rate

                                                total_dt += qty_at_dt * p
                                elif asset['asset_type'] == 'Renda Fixa':
                                    total_dt += float(asset['average_price'])

                            portfolio_values.append(total_dt)

                        # Preparar DataFrame de Performance
                        perf_df = pd.DataFrame({'Data': meses_fechamento, 'Portfolio': portfolio_values})
                        perf_df['Data'] = perf_df['Data'].dt.normalize()

                        # Encontrar o primeiro mês com saldo no portfólio para ancorar a rentabilidade (baseline)
                        non_zero_mask = perf_df['Portfolio'] > 0
                        if non_zero_mask.any():
                            first_idx = non_zero_mask.idxmax()
                        else:
                            first_idx = 0

                        base_val = perf_df['Portfolio'].iloc[first_idx]
                        perf_df['Portfolio %'] = 0.0
                        if base_val > 0:
                            perf_df.loc[first_idx:, 'Portfolio %'] = (perf_df.loc[first_idx:, 'Portfolio'] / base_val - 1) * 100

                        # 3. Processar Índices
                        # CDI Acumulado
                        cdi_vals = indices['cdi']
                        perf_df['CDI %'] = 0.0
                        if not cdi_vals.empty:
                            if cdi_vals.index.tz is not None: cdi_vals.index = cdi_vals.index.tz_localize(None)
                            cdi_vals.index = pd.to_datetime(cdi_vals.index).normalize()
                            # Acumular. CDI vem em % mensal.
                            cdi_cum = (1 + cdi_vals / 100).cumprod()
                            # Reindexar para todas as datas do intervalo para preencher lacunas
                            full_range = pd.date_range(start=cdi_cum.index.min(), end=perf_df['Data'].max(), freq='D')
                            cdi_cum_daily = cdi_cum.reindex(full_range).ffill().bfill()
                            # Agora resample para as datas do gráfico
                            cdi_resampled = cdi_cum_daily.reindex(perf_df['Data']).ffill().bfill()
                            if not cdi_resampled.empty and cdi_resampled.iloc[first_idx] != 0:
                                cdi_base = cdi_resampled.iloc[first_idx]
                                perf_df.loc[first_idx:, 'CDI %'] = ((cdi_resampled.iloc[first_idx:] / cdi_base - 1) * 100).values

                        # IPCA Acumulado
                        ipca_vals = indices['ipca']
                        perf_df['IPCA %'] = 0.0
                        if not ipca_vals.empty:
                            if ipca_vals.index.tz is not None: ipca_vals.index = ipca_vals.index.tz_localize(None)
                            ipca_vals.index = pd.to_datetime(ipca_vals.index).normalize()
                            # Acumular. IPCA vem em % mensal (SGS 433).
                            ipca_cum = (1 + ipca_vals / 100).cumprod()
                            
                            full_range = pd.date_range(start=ipca_cum.index.min(), end=perf_df['Data'].max(), freq='D')
                            ipca_cum_daily = ipca_cum.reindex(full_range).ffill().bfill()
                            # Agora resample para as datas do gráfico
                            ipca_resampled = ipca_cum_daily.reindex(perf_df['Data']).ffill().bfill()
                            if not ipca_resampled.empty and ipca_resampled.iloc[first_idx] != 0:
                                ipca_base = ipca_resampled.iloc[first_idx]
                                perf_df.loc[first_idx:, 'IPCA %'] = ((ipca_resampled.iloc[first_idx:] / ipca_base - 1) * 100).values

                        # IBOV %
                        ibov_h = indices['ibov']
                        perf_df['IBOV %'] = 0.0
                        if not ibov_h.empty:
                            if ibov_h.index.tz is not None: ibov_h.index = ibov_h.index.tz_localize(None)
                            full_range = pd.date_range(start=ibov_h.index.min(), end=perf_df['Data'].max(), freq='D')
                            ibov_daily = ibov_h.reindex(full_range).ffill().bfill()
                            ibov_m = ibov_daily.reindex(perf_df['Data']).ffill().bfill()
                            if not ibov_m.empty and ibov_m.iloc[first_idx] != 0:
                                ibov_base = ibov_m.iloc[first_idx]
                                perf_df.loc[first_idx:, 'IBOV %'] = ((ibov_m.iloc[first_idx:] / ibov_base - 1) * 100).values

                        # IFIX %
                        # Se IFIX via YF falhar (poucos dados), tentamos manter se houver algo
                        ifix_h = indices['ifix']
                        perf_df['IFIX %'] = 0.0
                        if not ifix_h.empty and len(ifix_h) > 1:
                            if ifix_h.index.tz is not None: ifix_h.index = ifix_h.index.tz_localize(None)
                            full_range = pd.date_range(start=ifix_h.index.min(), end=perf_df['Data'].max(), freq='D')
                            ifix_daily = ifix_h.reindex(full_range).ffill().bfill()
                            ifix_m = ifix_daily.reindex(perf_df['Data']).ffill().bfill()
                            if not ifix_m.empty and ifix_m.iloc[first_idx] != 0:
                                ifix_base = ifix_m.iloc[first_idx]
                                perf_df.loc[first_idx:, 'IFIX %'] = ((ifix_m.iloc[first_idx:] / ifix_base - 1) * 100).values

                    if 'perf_df' in locals():
                        st.session_state.perf_v5 = {'user_id': st.session_state.user_id, 'perf_df': perf_df}
                        all_assets_user_empty = perf_df.empty
                        
                        # Alerta visual se algum índice falhou na busca (ajuda a diagnosticar bloqueios de API)
                        if not all_assets_user_empty:
                            failed_indices = []
                            if indices['ipca'].empty: failed_indices.append("IPCA")
                            if indices['cdi'].empty: failed_indices.append("CDI")
                            if indices['ibov'].empty: failed_indices.append("IBOV")
                            if failed_indices:
                                st.warning(f"⚠️ Alguns índices ({', '.join(failed_indices)}) não puderam ser atualizados e podem aparecer zerados.")
                    else:
                        all_assets_user_empty = True

            if not all_assets_user_empty:
                # 4. Plotar Gráfico
                perf_df = perf_df.fillna(0.0)
                y_cols = [c for c in ['Portfolio %', 'CDI %', 'IBOV %', 'IFIX %', 'IPCA %'] if c in perf_df.columns]
                fig_perf = px.line(
                    perf_df, x='Data', 
                    y=y_cols,
                    title='Rentabilidade Acumulada (%) - Últimos 12 Meses',
                    labels={'value': 'Rentabilidade (%)', 'variable': 'Indicador'},
                    markers=True
                )
                fig_perf.update_layout(
                    hovermode="x unified", 
                    yaxis=dict(ticksuffix="%", hoverformat=".2f"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_perf, use_container_width=True)
            else:
                st.info("Adicione ativos para visualizar o gráfico de performance.")
                    
        with tab_setores:
            rv_assets = assets_df[assets_df['asset_type'] != 'Renda Fixa']
            if not rv_assets.empty and total_renda_variavel > 0:
                sector_df = rv_assets.groupby('sector')['current_value'].sum().reset_index()
                sector_df['percent'] = (sector_df['current_value'] / total_renda_variavel) * 100
                sector_df = sector_df.sort_values(by='percent', ascending=False)
                
                fig_sect = px.bar(
                    sector_df, 
                    x='sector', 
                    y='percent', 
                    title='Peso dos Setores na Renda Variável (%)', 
                    text_auto='.2f',
                    labels={'sector': 'Setor', 'percent': 'Peso (%)'}
                )
                fig_sect.update_layout(clickmode='event+select')
                event_sect = st.plotly_chart(fig_sect, use_container_width=True, on_select="rerun", key="bar_chart_sector")
                
                if event_sect and event_sect.selection and event_sect.selection.points:
                    selected_sector = event_sect.selection.points[0].get("x", "")
                    
                    if selected_sector and st.session_state.get('last_sector_selection') != selected_sector:
                        st.session_state.sector_dialog_handled = False
                        st.session_state.last_sector_selection = selected_sector
                        
                    if not st.session_state.get('sector_dialog_handled'):
                        dialog_assets_by_sector(selected_sector, rv_assets)
            else:
                st.info("Adicione ativos de Renda Variável para visualizar esta distribuição.")
                
        if tab_us:
            with tab_us:
                us_assets = assets_df[assets_df['asset_type'].isin(['Stocks', 'Reits'])]
                if not us_assets.empty and us_assets['current_value'].sum() > 0:
                    us_df = us_assets.groupby('ticker')['current_value'].sum().reset_index()
                    us_df = us_df.sort_values(by='current_value', ascending=False)
                    us_df['current_value_formatted'] = us_df['current_value'].apply(format_brl)
                    us_df['ticker_display'] = us_df['ticker'].apply(format_ticker_for_display)
                    fig_us = px.bar(
                        us_df, 
                        x='ticker_display', 
                        y='current_value', 
                        title='Valor Total por Ativo Norte-Americano (R$)',
                        text='current_value_formatted',
                        labels={'ticker': 'Ticker', 'current_value': 'Valor Atual (R$)'}
                    )
                    fig_us.update_traces(textposition='outside')
                    st.plotly_chart(fig_us, use_container_width=True)
                
                    all_prov_db = db.get_proventos(st.session_state.user_id)
                    if not all_prov_db.empty:
                        with db.get_db_connection() as conn:
                            full_assets_map_all = {row['ticker']: row['asset_type'] for _, row in pd.read_sql_query("SELECT ticker, asset_type FROM assets", conn).iterrows()}
                    
                        all_prov_tickers = all_prov_db['ticker'].unique()
                        us_tickers_all = [t for t in all_prov_tickers if full_assets_map_all.get(t, infer_asset_type(t)) in ['Stocks', 'Reits']]
                        df_us_prov_all = all_prov_db[all_prov_db['ticker'].isin(us_tickers_all)]
                    
                        if not df_us_prov_all.empty:
                            st.markdown("---")
                            resumo_usd = df_us_prov_all.groupby('ano')['valor'].sum().reset_index()
                            usd_to_brl_rate_local = svc.get_usd_brl_rate(st.session_state.refresh_id)
                            if usd_to_brl_rate_local <= 0: usd_to_brl_rate_local = 1.0
                            resumo_usd['valor_usd'] = resumo_usd['valor'] / usd_to_brl_rate_local
                            resumo_usd.columns = ['Ano', 'Valor BRL', 'Valor USD']
                            resumo_usd['Ano'] = resumo_usd['Ano'].astype(str)
                            resumo_usd = resumo_usd.sort_values('Ano', ascending=True)
                        
                            fig_rp_usd = px.bar(
                                resumo_usd,
                                x='Ano',
                                y='Valor USD',
                                title='Evolução da Renda Passiva em USD$ (Stocks e Reits)',
                                text_auto='.2r',
                                labels={'Valor USD': 'Total Anual (USD$)'}
                            )
                            x_data_usd = np.arange(len(resumo_usd))
                            y_data_usd = resumo_usd['Valor USD'].values
                            if len(x_data_usd) > 1:
                                z_usd = np.polyfit(x_data_usd, y_data_usd, 1)
                                p_usd = np.poly1d(z_usd)
                                fig_rp_usd.add_scatter(x=resumo_usd['Ano'], y=p_usd(x_data_usd), mode='lines', name='Tendência', line=dict(color='yellow', dash='dash'))
                        
                            fig_rp_usd.update_xaxes(type='category')
                            st.plotly_chart(fig_rp_usd, use_container_width=True)
                else:
                    st.info("Nenhum ativo do tipo Stocks ou Reits encontrado no portfólio.")
        with tab_fii:
            fii_assets = assets_df[assets_df['asset_type'] == 'Fiis'].copy()
            if not fii_assets.empty and fii_assets['current_value'].sum() > 0:
                # Lógica para Recebíveis x Tijolos
                def classify_fii(row):
                    ticker = row['ticker']
                    sector = row['sector']
                    
                    # Regras específicas conforme solicitado
                    if ticker in ['KNCA11.SA', 'MCRE11.SA']:
                        return 'Recebíveis'
                        
                    recebiveis_types = ['Recebíveis', 'Hedge Funds', 'Papel / Crédito']
                    if sector in recebiveis_types:
                        return 'Recebíveis'
                    return 'Tijolo'
                
                fii_assets['classe'] = fii_assets.apply(classify_fii, axis=1)
                
                # Lógica Especial para KNHF11 (60% Recebíveis / 40% Tijolo)
                chart_df = fii_assets.copy()
                knhf_mask = chart_df['ticker'] == 'KNHF11.SA'
                if knhf_mask.any():
                    knhf_data = chart_df[knhf_mask].iloc[0]
                    # Remove original
                    chart_df = chart_df[~knhf_mask]
                    # Adiciona 60% Recebíveis
                    row_rec = knhf_data.copy()
                    row_rec['current_value'] = knhf_data['current_value'] * 0.6
                    row_rec['classe'] = 'Recebíveis'
                    # Adiciona 40% Tijolo
                    row_tij = knhf_data.copy()
                    row_tij['current_value'] = knhf_data['current_value'] * 0.4
                    row_tij['classe'] = 'Tijolo'
                    
                    chart_df = pd.concat([chart_df, pd.DataFrame([row_rec, row_tij])], ignore_index=True)
    
                col_fii1, col_fii2, col_fii3 = st.columns(3)
                with col_fii1:
                    fii_assets['ticker_display'] = fii_assets['ticker'].apply(format_ticker_for_display)
                    fig_fii = px.pie(
                        fii_assets, 
                        values='current_value', 
                        names='ticker_display', 
                        title='Distribuição por Ticker', 
                        hole=0.4
                    )
                    st.plotly_chart(fig_fii, use_container_width=True)
                with col_fii2:
                    fii_sect_df = fii_assets.groupby('sector')['current_value'].sum().reset_index()
                    fig_fii_sect = px.bar(
                        fii_sect_df, 
                        x='sector',
                        y='current_value', 
                        title='Distribuição por Segmento', 
                        text_auto='.2s'
                    )
                    fig_fii_sect.update_layout(clickmode='event+select', showlegend=False, xaxis_title="Segmento", yaxis_title="")
                    event_fii_sect = st.plotly_chart(fig_fii_sect, use_container_width=True, on_select="rerun", key="bar_fii_sect")
                    
                    if event_fii_sect and event_fii_sect.selection and event_fii_sect.selection.points:
                        selected_sector = event_fii_sect.selection.points[0].get("x", "")
                        if selected_sector and st.session_state.get('last_fii_sect_selection') != selected_sector:
                            st.session_state.sector_dialog_handled = False
                            st.session_state.last_fii_sect_selection = selected_sector
                        if not st.session_state.get('sector_dialog_handled'):
                            dialog_assets_by_sector(selected_sector, fii_assets)
                with col_fii3:
                    class_df = chart_df.groupby('classe')['current_value'].sum().reset_index()
                    total_fii_value = class_df['current_value'].sum()
                    class_df['percent'] = (class_df['current_value'] / total_fii_value) * 100 if total_fii_value > 0 else 0
                    
                    fig_fii_class = px.bar(
                        class_df, 
                        x='classe',
                        y='percent', 
                        title='Recebíveis x Tijolos (%)', 
                        color='classe',
                        color_discrete_map={'Tijolo': '#00CC96', 'Recebíveis': '#636EFA'},
                        text_auto='.1f'
                    )
                    fig_fii_class.update_layout(clickmode='event+select', showlegend=False, xaxis_title="Classe", yaxis_title="Percentual (%)")
                    fig_fii_class.update_traces(textsuffix='%', textposition='outside')
                    event_fii_class = st.plotly_chart(fig_fii_class, use_container_width=True, on_select="rerun", key="bar_fii_class")
                    
                    if event_fii_class and event_fii_class.selection and event_fii_class.selection.points:
                        selected_class = event_fii_class.selection.points[0].get("x", "")
                        if selected_class and st.session_state.get('last_fii_class_selection') != selected_class:
                            st.session_state.fii_class_dialog_handled = False
                            st.session_state.last_fii_class_selection = selected_class
                        if not st.session_state.get('fii_class_dialog_handled'):
                            dialog_fiis_by_class(selected_class, chart_df)
                
                st.markdown("---")
                # NOVO GRÁFICO: Proventos Fiis
                st.subheader("📊 Proventos Fiis")
                current_fii_tickers = fii_assets['ticker'].unique()
                fii_prov_data = []
                for t in current_fii_tickers:
                    total_p = db.get_total_proventos_by_ticker(t, st.session_state.user_id)
                    fii_prov_data.append({'Ativo': t, 'Total Proventos': total_p})
                
                fii_prov_df = pd.DataFrame(fii_prov_data).sort_values(by='Total Proventos', ascending=True)
                if not fii_prov_df.empty and fii_prov_df['Total Proventos'].sum() > 0:
                    fii_prov_df['Ativo_display'] = fii_prov_df['Ativo'].apply(format_ticker_for_display)
                    fig_fii_p = px.bar(
                        fii_prov_df, 
                        x='Ativo_display', 
                        y='Total Proventos', 
                        title='Proventos Fiis (Acumulado Histórico)',
                        text_auto='.2r',
                        labels={'Total Proventos': 'Total Recebido (R$)'}
                    )
                    st.plotly_chart(fig_fii_p, use_container_width=True)
                else:
                    st.info("Ainda não há histórico de proventos para os FIIs na carteira.")
                    
                # NOVO GRÁFICO: Retorno Total Fiis
                st.markdown("---")
                st.subheader("💰 Retorno Total Fiis")
                
                fii_return_data = []
                for t in current_fii_tickers:
                    # Get profit_loss from fii_assets
                    asset_row = fii_assets[fii_assets['ticker'] == t]
                    profit_loss = asset_row['profit_loss'].sum() if not asset_row.empty else 0.0
                    
                    # Get total proventos
                    total_p = df_prov_dict.get(t, db.get_total_proventos_by_ticker(t, st.session_state.user_id)) if 'df_prov_dict' in locals() else db.get_total_proventos_by_ticker(t, st.session_state.user_id)
                    
                    # Retorno Total = (Cotação Atual * Qtd - Preço Médio * Qtd) + Proventos Recebidos
                    total_return = profit_loss + total_p
                    fii_return_data.append({'Ativo': t, 'Retorno Total': total_return})
                    
                fii_return_df = pd.DataFrame(fii_return_data).sort_values(by='Retorno Total', ascending=True)
                
                if not fii_return_df.empty:
                    # Definir cores: verde se positivo, vermelho se negativo
                    colors = ['#EF553B' if val < 0 else '#00CC96' for val in fii_return_df['Retorno Total']]
                    
                    fii_return_df['Ativo_display'] = fii_return_df['Ativo'].apply(format_ticker_for_display)
                    fig_fii_ret = px.bar(
                        fii_return_df,
                        x='Ativo_display',
                        y='Retorno Total',
                        title='Retorno Total por Ativo (Capital + Proventos)',
                        text_auto='.2f',
                        labels={'Retorno Total': 'Retorno Total (R$)'}
                    )
                    fig_fii_ret.update_traces(marker_color=colors)
                    st.plotly_chart(fig_fii_ret, use_container_width=True)
                else:
                    st.info("Nenhum dado suficiente para calcular o retorno total dos FIIs.")
                    
            else:
                st.info("Nenhum Fundo Imobiliário (Fiis) encontrado no portfólio.")
    
        with tab_passiva:
            # Gráficos de Renda Passiva
            all_prov_db = db.get_proventos(st.session_state.user_id)
            if not all_prov_db.empty:
                anos_prov = sorted(all_prov_db['ano'].unique().tolist())
                resumo_graph = get_annual_proventos_summary(all_prov_db, anos_prov)
                
                if not resumo_graph.empty:
                    col_rp1, col_rp2 = st.columns(2)
                    
                    with col_rp1:
                        fig_rp_mensal = px.bar(
                            resumo_graph,
                            x='Ano',
                            y='Valor Mensal',
                            title='Evolução da Renda Passiva Mensal (Média)',
                            text_auto='.2r',
                            labels={'Valor Mensal': 'Média Mensal (R$)'}
                        )
                        # Adiciona Linha de Tendência
                        x_data = np.arange(len(resumo_graph))
                        y_data = resumo_graph['Valor Mensal'].values
                        if len(x_data) > 1:
                            z = np.polyfit(x_data, y_data, 1)
                            p = np.poly1d(z)
                            fig_rp_mensal.add_scatter(x=resumo_graph['Ano'], y=p(x_data), mode='lines', name='Tendência', line=dict(color='yellow', dash='dash'))
                        
                        fig_rp_mensal.update_xaxes(type='category')
                        st.plotly_chart(fig_rp_mensal, use_container_width=True)
                        
                    with col_rp2:
                        fig_rp_anual = px.bar(
                            resumo_graph,
                            x='Ano',
                            y='Valor Anual',
                            title='Evolução da Renda Passiva Anual',
                            text_auto='.2r',
                            labels={'Valor Anual': 'Total Anual (R$)'}
                        )
                        # Adiciona Linha de Tendência
                        y_data_tot = resumo_graph['Valor Anual'].values
                        if len(x_data) > 1:
                            z_tot = np.polyfit(x_data, y_data_tot, 1)
                            p_tot = np.poly1d(z_tot)
                            fig_rp_anual.add_scatter(x=resumo_graph['Ano'], y=p_tot(x_data), mode='lines', name='Tendência', line=dict(color='yellow', dash='dash'))
                            
                        fig_rp_anual.update_xaxes(type='category')
                        st.plotly_chart(fig_rp_anual, use_container_width=True)
    
                    st.markdown("---")
                    st.markdown('<h3 style="color: #ffffff; font-size: 1.2rem; margin-bottom: 1rem;">📊 Relação Dividendo Médio Mensal x Salário Mínimo</h3>', unsafe_allow_html=True)
                    
                    # Dicionário do Salário Mínimo Vigente no Brasil (2018 em diante)
                    salario_minimo_hist = {
                        2018: 954.00,
                        2019: 998.00,
                        2020: 1045.00,
                        2021: 1100.00,
                        2022: 1212.00,
                        2023: 1320.00,
                        2024: 1412.00,
                        2025: 1518.00,
                        2026: 1621.00
                    }
                    
                    index_rows = []
                    for idx, row in resumo_graph.iterrows():
                        try:
                            ano_int = int(row['Ano'])
                        except Exception as e:
                            import logging
                            logging.warning(f"Aviso ao processar ano do resumo_graph: {e}")
                            continue
                            
                        if ano_int >= 2018:
                            max_ano_dict = max(salario_minimo_hist.keys())
                            salario = salario_minimo_hist.get(ano_int, salario_minimo_hist[max_ano_dict])
                            
                            mensal_medio = row['Valor Mensal']
                            dividendo_recebido = mensal_medio / salario if salario > 0 else 0
                            
                            index_rows.append({
                                'Ano': str(ano_int),
                                'Salário Minimo': salario,
                                'Dividendo Mensal': mensal_medio,
                                'Relação Div / Sal Minimo': dividendo_recebido
                            })
                    
                    if index_rows:
                        df_indexador = pd.DataFrame(index_rows)
                        display_indexador = df_indexador.copy()
                        display_indexador['Salário Minimo'] = display_indexador['Salário Minimo'].apply(format_brl)
                        display_indexador['Dividendo Mensal'] = display_indexador['Dividendo Mensal'].apply(format_brl)
                        display_indexador['Relação Div / Sal Minimo'] = display_indexador['Relação Div / Sal Minimo'].apply(lambda x: f"{x:,.2f}".replace('.', ','))
                        
                        styled_indexador = display_indexador.style.set_properties(**{'text-align': 'center'}, subset=['Ano', 'Salário Minimo', 'Dividendo Mensal', 'Relação Div / Sal Minimo'])
                        
                        col_idx_tbl, col_idx_chart = st.columns(2)
                        with col_idx_tbl:
                            st.dataframe(styled_indexador, hide_index=True, use_container_width=True)
                        
                        with col_idx_chart:
                            fig_idx = px.bar(
                                df_indexador,
                                x='Ano',
                                y='Relação Div / Sal Minimo',
                                title='Evolução Proventos x Salário Mínimo',
                                text_auto='.2f',
                                labels={'Relação Div / Sal Minimo': 'Multiplicador'}
                            )
                            # Adiciona Linha de Tendência
                            x_data_idx = np.arange(len(df_indexador))
                            y_data_idx = df_indexador['Relação Div / Sal Minimo'].values
                            if len(x_data_idx) > 1:
                                z_idx = np.polyfit(x_data_idx, y_data_idx, 1)
                                p_idx = np.poly1d(z_idx)
                                fig_idx.add_scatter(x=df_indexador['Ano'], y=p_idx(x_data_idx), mode='lines', name='Tendência', line=dict(color='yellow', dash='dash'))
                                
                            fig_idx.update_xaxes(type='category')
                            st.plotly_chart(fig_idx, use_container_width=True)
    
                    # Código da evolução de US$ foi movido para tab_us
                else:
                    st.info("Dados insuficientes para gerar gráficos de renda passiva.")
            else:
                st.info("Registre proventos para visualizar a evolução da renda passiva.")
    
        if has_options_data and tab_sinteticos:
            with tab_sinteticos:
                # Gráficos de Dividendos Sintéticos (Vl Prêmio de Opções)
                opcoes_db = db.get_opcoes(st.session_state.user_id)
                if not opcoes_db.empty:
                    opcoes_db['ano'] = pd.to_datetime(opcoes_db['dt_operacao']).dt.year
                    resumo_sintetico = opcoes_db.groupby('ano')['vl_premio'].sum().reset_index()
                    resumo_sintetico['ano'] = resumo_sintetico['ano'].astype(str)
                    resumo_sintetico = resumo_sintetico.sort_values('ano', ascending=True)
                    
                    st.markdown('<h3 style="color: #ffffff; font-size: 1.2rem; margin-bottom: 1rem;">💰 Evolução de Dividendos Sintéticos</h3>', unsafe_allow_html=True)
                    
                    colors_sint = ['#EF553B' if val < 0 else '#636EFA' for val in resumo_sintetico['vl_premio']]
                    
                    fig_sint = px.bar(
                        resumo_sintetico,
                        x='ano',
                        y='vl_premio',
                        title='Total Anual de Prêmios Recebidos (R$)',
                        text_auto='.2f',
                        labels={'vl_premio': 'Total Prêmio (R$)', 'ano': 'Ano'}
                    )
                    fig_sint.update_traces(marker_color=colors_sint)
                    
                    x_data_sint = np.arange(len(resumo_sintetico))
                    y_data_sint = resumo_sintetico['vl_premio'].values
                    if len(x_data_sint) > 1:
                        z_sint = np.polyfit(x_data_sint, y_data_sint, 1)
                        p_sint = np.poly1d(z_sint)
                        fig_sint.add_scatter(x=resumo_sintetico['ano'], y=p_sint(x_data_sint), mode='lines', name='Tendência', line=dict(color='yellow', dash='dash'))
                        
                    fig_sint.update_xaxes(type='category')
                    st.plotly_chart(fig_sint, use_container_width=True)
                else:
                    st.info("Não há registros de opções para apresentar o gráfico de dividendos sintéticos. Vá para a aba Derivativos e importe seus dados.")
