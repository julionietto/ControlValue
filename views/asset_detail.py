import streamlit as st
import pandas as pd
import db
import services as svc
import plotly.express as px
import numpy as np
import time
from utils.formatters import format_ticker_for_display, escape_html, format_brl, infer_asset_type
from components.ui import create_card, render_top_header

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
            st.session_state.navigation_tab = "Visão Geral"
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
            st.session_state.show_confirm_delete_op = False
            st.session_state.refresh_id += 1 # Garante o reset total da tabela
            
            # Preserva os preços atuais em memória antes de recarregar do DB
            old_data = st.session_state.get('viewing_history', {})
            curr_p = old_data.get('current_price', 0.0)
            orig_p = old_data.get('original_current_price', 0.0)
            
            new_data = db.get_asset_by_id(asset_id, st.session_state.user_id)
            if new_data:
                new_data['current_price'] = curr_p
                new_data['original_current_price'] = orig_p
                st.session_state.viewing_history = new_data
                
            st.success("Operação excluída com sucesso!")
            st.rerun()
    with col_no:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.show_confirm_delete_op = False
            st.session_state.refresh_id += 1 # Reset selection
            st.rerun()

@st.dialog("Aviso: Conversão de Moeda")
def usd_conversion_notice_dialog():
    st.warning("Investimentos em Dólar")
    st.write("Os ativos do Tipo **Stocks, Reits ou Cripto** têm suas operações registradas em dólar.")
    st.write("Para fazer uma comparação com o CDI brasileiro, os valores das compras e as cotações históricas são convertidos para o **Real brasileiro** com base no câmbio da época.")
    
    if st.button("Entendido", type="primary", use_container_width=True):
        st.session_state[f"auth_chart_{st.session_state.get('last_ticker', 'global')}"] = True
        st.rerun()

def get_crypto_ticker(ticker):
    """Ajusta o ticker de cripto para o formato do Yahoo Finance."""
    if '-' in ticker: return ticker
    if ticker in ['BTC', 'ETH', 'SOL', 'USDT', 'USDC']:
        return f"{ticker}-USD"
    return ticker

@st.dialog("Histórico de Proventos", dismissible=False)
def dialog_consultar_proventos(ticker):
    import db
    st.markdown(f"**Proventos de:** `{ticker}`")
    prov_df = db.get_proventos(st.session_state.user_id)
    prov_df = prov_df[prov_df['ticker'] == ticker].copy()
    
    # [v1.2.5] Filtrar registros com valor zerado
    prov_df = prov_df[prov_df['valor'] > 0]
    
    if prov_df.empty:
        st.info("Nenhum provento recebido registrado para este ativo.")
    else:
        # Ordenação por data (Mês/Ano)
        meses_nomes_dict = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
        prov_df = prov_df.sort_values(['ano', 'mes'], ascending=True)
        prov_df['mes_str'] = prov_df['mes'].map(meses_nomes_dict)
        
        display_df = prov_df[['mes_str', 'ano', 'valor']].copy()
        display_df.columns = ['Mês', 'Ano', 'Valor']
        
        total_prov = display_df['Valor'].sum()
        
        st.dataframe(display_df, hide_index=True, use_container_width=True)
        st.markdown(f"**Total Recebido:** R$ {total_prov:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
    if st.button("Fechar", use_container_width=True):
        st.rerun()

def render_asset_detail_view(asset_data):
    if not asset_data:
        st.session_state.navigation_tab = "Visão Geral"
        st.rerun()

    ticker = asset_data['ticker']
    display_ticker = format_ticker_for_display(ticker)
    
    # Lógica de Refresh Imediato para Cripto (Independente de horário de bolsa)
    current_type = asset_data.get('asset_type', '')
    if current_type == 'Cripto' and st.session_state.get('detail_refreshed_ticker') != ticker:
        ticker_to_fetch = ticker
        if '-' not in ticker and ticker in ['BTC', 'ETH', 'SOL', 'USDT', 'USDC']:
            ticker_to_fetch = f"{ticker}-USD"
            
        try:
            # Força busca com refresh_id único (timestamp) para ignorar cache de 5min
            fresh_prices = svc.fetch_current_prices([ticker_to_fetch], refresh_id=int(time.time()))
            new_native_price = fresh_prices.get(ticker_to_fetch, 0.0)
            
            if new_native_price > 0:
                # Atualiza também a taxa do dólar (forçando busca)
                rate = svc.get_usd_brl_rate(refresh_id=int(time.time()), is_first_load=True)
                new_brl_price = new_native_price * rate if rate > 0 else 0.0
                
                # Atualiza o estado global e o snapshot local
                st.session_state.viewing_history['original_current_price'] = new_native_price
                st.session_state.viewing_history['current_price'] = new_brl_price
                asset_data['original_current_price'] = new_native_price
                asset_data['current_price'] = new_brl_price
                
                st.session_state.detail_refreshed_ticker = ticker
        except Exception as e:
            import logging
            logging.warning(f"Erro no refresh de cripto: {e}")
    
    # HEADER INTERNALIZED - This forces a native scroll reset on navigation
    render_top_header(f"Detalhe do Ativo: {display_ticker}", "Análise detalhada e gerenciamento de operações.")

    # Âncora invisível para o scroll-to-top (Backup JS)
    st.markdown('<div id="detalhe-ativo-topo"></div>', unsafe_allow_html=True)

    # Forçar scroll para o topo (JavaScript de redundância)
    if st.session_state.pop('scroll_to_top', False):
        st.components.v1.html(
            """
            <script>
                function forceScroll() {
                    // Seletores para os containers de scroll do Streamlit (podem mudar entre versões)
                    const selectors = [
                        "section.stMain", 
                        ".stAppViewMain .stMain", 
                        "section.main", 
                        ".main", 
                        "[data-testid='stMainView']",
                        "[data-testid='stAppViewMain']"
                    ];
                    
                    const parentDoc = window.parent.document;
                    
                    selectors.forEach(sel => {
                        const el = parentDoc.querySelector(sel);
                        if (el) {
                            el.scrollTo({ top: 0, behavior: 'instant' });
                            el.scrollTop = 0;
                        }
                    });
                    
                    // Fallback para a janela principal
                    window.parent.scrollTo(0, 0);
                }
                
                // Executa em sequência para garantir que pegue após o re-render
                forceScroll();
                setTimeout(forceScroll, 50);
                setTimeout(forceScroll, 150);
                setTimeout(forceScroll, 300);
                setTimeout(forceScroll, 600);
            </script>
            """,
            height=0
        )
    
    asset_id = asset_data['id']
    current_type = asset_data['asset_type']

    @st.dialog("Adicionar Operação", dismissible=False)
    def dialog_add_operation():
        st.markdown(f"**Ativo:** `{display_ticker}`<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        op_type = st.radio("Tipo de Operação", ["Compra", "Venda"], horizontal=True, key="add_op_type")
        op_date = st.date_input("Data", value=pd.Timestamp.now().date(), max_value=pd.Timestamp.now().date(), format="DD/MM/YYYY", key="add_op_date")
        
        if current_type in ['Ações', 'Fiis', 'ETF', 'Stocks', 'Reits']:
            op_qty_input = st.number_input("Quantidade", min_value=1, step=1, format="%d", key="add_op_qty")
            op_price = st.number_input("Preço", min_value=0.01, step=0.01, format="%.2f", key="add_op_price")
        else:
            op_qty_input = st.number_input("Quantidade", min_value=0.00000001, step=0.00001, format="%.8f", key="add_op_qty")
            op_price = st.number_input("Preço", min_value=0.01, step=0.01, format="%.2f", key="add_op_price")
            
        st.markdown("")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("Confirmar", type="primary", use_container_width=True, key="confirm_add"):
                final_qty = -abs(op_qty_input) if op_type == "Venda" else abs(op_qty_input)
                db.add_asset_operation(asset_id, st.session_state.user_id, op_date.strftime("%Y-%m-%d"), final_qty, op_price)
                st.success(f"Operação de {'Compra' if op_type == 'Compra' else 'Venda'} adicionada!")
                st.rerun()
        with col_c2:
            if st.button("Cancelar", use_container_width=True, key="cancel_add"):
                st.rerun()

    @st.dialog("Editar Operação", dismissible=False)
    def dialog_edit_operation(op_data):
        st.markdown(f"**Editando Operação - Ativo:** `{display_ticker}`<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        try:
            current_date_obj = pd.to_datetime(op_data['date']).date()
        except:
            current_date_obj = pd.Timestamp.now().date()
            
        op_type = st.radio("Tipo de Operação", ["Compra", "Venda"], index=0 if op_data['quantity'] >= 0 else 1, horizontal=True, key=f"edit_op_type_{op_data['id']}")
        op_date = st.date_input("Data", value=current_date_obj, max_value=pd.Timestamp.now().date(), format="DD/MM/YYYY", key=f"edit_op_date_{op_data['id']}")
        
        initial_qty = abs(op_data['quantity'])
        if current_type in ['Ações', 'Fiis', 'ETF', 'Stocks', 'Reits']:
            op_qty_input = st.number_input("Quantidade", min_value=1, step=1, format="%d", value=int(initial_qty), key=f"edit_op_qty_{op_data['id']}")
            op_price = st.number_input("Preço", min_value=0.01, step=0.01, format="%.2f", value=float(op_data['unit_price']), key=f"edit_op_price_{op_data['id']}")
        else:
            op_qty_input = st.number_input("Quantidade", min_value=0.00000001, step=0.00001, format="%.8f", value=float(initial_qty), key=f"edit_op_qty_{op_data['id']}")
            op_price = st.number_input("Preço", min_value=0.01, step=0.01, format="%.2f", value=float(op_data['unit_price']), key=f"edit_op_price_{op_data['id']}")
            
        st.markdown("")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            if st.button("Salvar", type="primary", use_container_width=True, key=f"save_edit_{op_data['id']}"):
                final_qty = -abs(op_qty_input) if op_type == "Venda" else abs(op_qty_input)
                target_asset_id = op_data['asset_id'] if 'asset_id' in op_data else asset_id
                db.update_asset_operation(op_data['id'], target_asset_id, st.session_state.user_id, op_date.strftime("%Y-%m-%d"), final_qty, op_price)
                
                # Preserva os preços atuais em memória antes de recarregar do DB
                old_data = st.session_state.get('viewing_history', {})
                curr_p = old_data.get('current_price', 0.0)
                orig_p = old_data.get('original_current_price', 0.0)
                
                new_data = db.get_asset_by_id(target_asset_id, st.session_state.user_id)
                if new_data:
                    new_data['current_price'] = curr_p
                    new_data['original_current_price'] = orig_p
                    st.session_state.viewing_history = new_data
                
                st.session_state.refresh_id += 1 # Reset selection to close dialog
                st.success("Operação atualizada!")
                st.rerun()
        with col_c2:
            if st.button("Excluir", type="secondary", use_container_width=True, key=f"delete_op_{op_data['id']}"):
                st.session_state.show_confirm_delete_op = True
                st.session_state.op_to_delete = op_data.to_dict()
                st.session_state.refresh_id += 1 # Limpa a seleção para permitir a abertura do próximo diálogo
                st.rerun()
        with col_c3:
            if st.button("Cancelar", use_container_width=True, key=f"cancel_edit_{op_data['id']}"):
                st.session_state.refresh_id += 1 # Reset selection to close dialog
                st.rerun()



    # Verifica se deve abrir os diálogos de confirmação
    if st.session_state.get('show_confirm_delete', False):
        asset_id_del = st.session_state.get('delete_asset_id')
        ticker_del = st.session_state.get('delete_asset_ticker')
        st.session_state.show_confirm_delete = False
        confirm_delete_dialog(asset_id_del, ticker_del)

    if st.session_state.get('show_confirm_delete_op', False):
        op_data_del = st.session_state.get('op_to_delete')
        st.session_state.show_confirm_delete_op = False
        confirm_delete_operation_dialog(op_data_del, asset_id)

    price_now_native = asset_data.get('original_current_price', 0.0)
    price_now_brl = asset_data.get('current_price', 0.0)
    price_ceiling = asset_data.get('price_ceiling', 0.0)
    fair_value = asset_data.get('fair_value', 0.0)
    avg_price_native = asset_data.get('average_price', 0.0)
    
    compare_init = price_now_brl if current_type == 'Cripto' else price_now_native
    init_guidance = "COMPRA" if (current_type == 'Renda Fixa' or compare_init <= price_ceiling) else "AGUARDE"
    
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f'<h2 style="color: #ffffff; margin-top: 0;">Valores Sumarizados</h2>', unsafe_allow_html=True)

    with col_h2:
        color = "#00CC96" if init_guidance == "COMPRA" else "#EF553B"
        st.markdown(f'<div style="background-color: {color}; color: white; padding: 6px 12px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 1.2rem;">{init_guidance}</div>', unsafe_allow_html=True)
        if current_type in ['Stocks', 'Reits']:
            st.markdown('<div style="color: #ffffff; font-size: 1rem; text-align: center; margin-top: 8px; font-weight: bold;">Valores em US$</div>', unsafe_allow_html=True)

    history_df = db.get_asset_history(asset_id, st.session_state.user_id)
    usd_to_brl_rate = svc.get_usd_brl_rate(st.session_state.refresh_id)
    
    total_investido = 0.0
    total_ativo = 0.0
    retorno_total = 0.0
    total_qtd = 0.0
    
    if not history_df.empty:
        foreign_types = ['Stocks', 'Reits']
        def convert_to_brl(val):
            return val * usd_to_brl_rate if asset_data['currency'] == 'USD' else val

        history_df['unit_price_brl'] = history_df['unit_price'].apply(convert_to_brl)
        history_df['valor_operacao'] = history_df['quantity'] * history_df['unit_price_brl']
        history_df['valor_atualizado'] = history_df['quantity'] * price_now_brl
        history_df['lucro_prejuizo'] = history_df['valor_atualizado'] - history_df['valor_operacao']
        history_df['ganho_pct'] = ((price_now_brl / history_df['unit_price_brl']) - 1) * 100
        
        total_investido = history_df['valor_operacao'].sum()
        total_ativo = history_df['valor_atualizado'].sum()
        retorno_total = history_df['lucro_prejuizo'].sum()
        total_qtd = history_df['quantity'].sum()
    elif current_type == 'Renda Fixa':
        total_investido = asset_data.get('total_invested', 0.0)
        total_ativo = asset_data.get('current_value', 0.0)
        retorno_total = asset_data.get('profit_loss', 0.0)
        total_qtd = asset_data.get('quantity', 0.0)
        
    total_proventos = db.get_total_proventos_by_ticker(ticker, st.session_state.user_id)
    is_us_asset = current_type in ['Stocks', 'Reits']
    display_symbol = "$" if is_us_asset else "R$"
    
    def format_qty_hist(qty, asset_type):
        if asset_type == 'Cripto':
            formatted = f"{qty:,.8f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if "," in formatted: formatted = formatted.rstrip('0').rstrip(',')
            return formatted
        return f"{qty:,.0f}".replace(",", ".")

    def format_details_val(val, show_symbol=True):
        fmt = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{display_symbol} {fmt}" if show_symbol else fmt

    if is_us_asset:
        total_investido_native = (history_df['quantity'] * history_df['unit_price']).sum() if not history_df.empty else 0.0
        total_ativo_native = (history_df['quantity'] * price_now_native).sum() if not history_df.empty else (total_qtd * price_now_native)
        retorno_total_native = total_ativo_native - total_investido_native
        total_proventos_usd = total_proventos / usd_to_brl_rate if usd_to_brl_rate > 0 else 0.0
        retorno_total_com_prov_native = retorno_total_native + total_proventos_usd
        retorno_total_pct = (retorno_total_com_prov_native / total_investido_native * 100) if total_investido_native > 0 else 0.0
        yield_on_cost = (total_proventos_usd / total_investido_native * 100) if total_investido_native > 0 else 0.0
        
        card_investido = format_details_val(total_investido_native)
        card_ativo = format_details_val(total_ativo_native)
        card_proventos = format_details_val(total_proventos_usd)
        card_retorno = format_details_val(retorno_total_com_prov_native)
    else:
        retorno_total_com_prov = retorno_total + total_proventos
        retorno_total_pct = (retorno_total_com_prov / total_investido * 100) if total_investido > 0 else 0.0
        yield_on_cost = (total_proventos / total_investido * 100) if total_investido > 0 else 0.0
        card_investido = format_brl(total_investido)
        card_ativo = format_brl(total_ativo)
        card_proventos = format_brl(total_proventos)
        card_retorno = format_brl(retorno_total_com_prov)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1: create_card("Total Investido", card_investido, small_font=True)
    with col2: create_card("Total do Ativo", card_ativo, small_font=True)
    with col3: create_card("Total de Proventos", card_proventos, small_font=True)
    ret_delta = f"{retorno_total_pct:,.2f}%".replace('.', ',')
    with col4: create_card("Retorno Total", card_retorno, ret_delta, small_font=True)
    yoc_formatted = f"{yield_on_cost:,.2f}%".replace('.', ',')
    with col5: create_card("Yeld On Cost", yoc_formatted, small_font=True)
    with col6: create_card("Quantidade Total", format_qty_hist(total_qtd, current_type), small_font=True)
    
    st.markdown("---")
    col_p1, col_p2, col_p3, col_p4, col_p5, col_p6, col_p7 = st.columns([1.2, 1, 1, 1, 1, 1, 0.8])
    currency_symbol = "$" if current_type in ['Stocks', 'Reits'] else "R$"
    
    with col_p1:
        asset_types = ["Ações", "Fiis", "ETF", "Cripto", "Reits", "Stocks", "Renda Fixa"]
        try: type_idx = asset_types.index(current_type)
        except ValueError: type_idx = 0
        new_asset_type = st.selectbox("Tipo de Ativo", asset_types, index=type_idx, disabled=(current_type == 'Renda Fixa'))
        
    with col_p2:
        new_currency = st.selectbox("Moeda de Origem", ["BRL", "USD"], index=0 if asset_data['currency'] == 'BRL' else 1, help="Moeda em que as operações foram registradas.")

    display_val, display_sym = (price_now_brl, "R$") if asset_data['currency'] == 'BRL' and current_type == 'Cripto' else (price_now_native, currency_symbol)
    
    with col_p3:
        if current_type == 'Renda Fixa':
            new_avg_price = st.number_input("Saldo Acumulado (R$)", min_value=0.0, format="%.2f", value=float(avg_price_native))
        else:
            st.text_input("Preço Médio", value=f"{currency_symbol} {avg_price_native:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), disabled=True)
            new_avg_price = asset_data.get('average_price', 0.0)
            
    with col_p4: new_price_ceiling = st.number_input(f"Preço Teto ({currency_symbol})", min_value=0.0, format="%.2f", value=float(price_ceiling), disabled=(current_type == 'Renda Fixa'))
    with col_p5: new_fair_value = st.number_input(f"Preço Justo ({currency_symbol})", min_value=0.0, format="%.2f", value=float(fair_value), disabled=(current_type == 'Renda Fixa'))
    with col_p6: st.text_input("Cotação Atual", value=f"{display_sym} {display_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), disabled=True)

    with col_p7:
        st.markdown('<div style="padding-top: 28px;"></div>', unsafe_allow_html=True)
        if st.button("Salvar", type="primary", use_container_width=True):
            if current_type != 'Renda Fixa' and history_df.empty:
                st.error("É necessário adicionar pelo menos uma operação antes de salvar o ativo.")
            else:
                db.update_asset(asset_id, st.session_state.user_id, ticker, new_asset_type, asset_data.get('quantity', 0.0), new_avg_price, new_price_ceiling, new_fair_value, currency=new_currency)
                st.session_state.viewing_history = None
                st.session_state.navigation_tab = "Visão Geral"
                st.session_state.table_key += 1
                st.success("Alterações salvas com sucesso!")
                st.rerun()
            
    if current_type != 'Renda Fixa':
        new_guidance = "COMPRA" if compare_init <= new_price_ceiling else "AGUARDE"
        if new_guidance != init_guidance:
            st.info(f"Nova Orientação baseado no Preço Teto: **{new_guidance}**")
            
    st.markdown("---")
    st.markdown("### Histórico de Operações")
    if history_df.empty:
        st.warning("Nenhum registro de operação encontrado para este ativo.")
    else:
        display_hist = pd.DataFrame()
        display_hist['Data'] = pd.to_datetime(history_df['date']).dt.strftime('%d/%m/%Y')
        display_hist['Operação'] = history_df['quantity'].apply(lambda x: "Compra" if x > 0 else "Venda")
        display_hist['Qtd'] = history_df.apply(lambda x: format_qty_hist(x['quantity'], current_type), axis=1)
        
        if is_us_asset:
            display_hist['Preço'] = history_df['unit_price'].apply(lambda x: format_details_val(x))
            display_hist['Valor Operação'] = (history_df['quantity'] * history_df['unit_price']).apply(lambda x: format_details_val(x))
            display_hist['% Ganho'] = (((price_now_native / history_df['unit_price']) - 1) * 100).apply(lambda x: f"{x:,.2f}%".replace('.', ','))
            display_hist['Vlr Atualizado'] = (history_df['quantity'] * price_now_native).apply(lambda x: format_details_val(x))
            display_hist['Lucro/Prej'] = ((history_df['quantity'] * price_now_native) - (history_df['quantity'] * history_df['unit_price'])).apply(lambda x: format_details_val(x))
        else:
            display_hist['Preço'] = history_df['unit_price_brl'].apply(format_brl)
            display_hist['Valor Operação'] = history_df['valor_operacao'].apply(format_brl)
            display_hist['% Ganho'] = history_df['ganho_pct'].apply(lambda x: f"{x:,.2f}%".replace('.', ','))
            display_hist['Vlr Atualizado'] = history_df['valor_atualizado'].apply(format_brl)
            display_hist['Lucro/Prej'] = history_df['lucro_prejuizo'].apply(format_brl)
        
        display_hist = display_hist.reset_index().rename(columns={'index': 'op_idx'})
        styled_hist = display_hist.style.set_properties(**{'text-align': 'center'}, subset=['Data', 'Operação', 'Qtd']) \
                                       .set_properties(**{'text-align': 'right'}, subset=['Preço', 'Valor Operação', '% Ganho', 'Vlr Atualizado', 'Lucro/Prej'])
        selected_op = st.dataframe(styled_hist, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", column_config={"op_idx": None}, key=f"history_df_{asset_id}_{st.session_state.refresh_id}")
        if selected_op.selection.rows:
            row_idx = selected_op.selection.rows[0]
            if row_idx < len(history_df): dialog_edit_operation(history_df.iloc[row_idx])

    st.markdown("---")
    col_add, col_prov, col_del, col_voltar = st.columns(4)
    with col_add:
        if current_type != 'Renda Fixa' and st.button("Adicionar Operação", type="primary", use_container_width=True): dialog_add_operation()
    with col_prov:
        if current_type != 'Renda Fixa' and st.button("Consultar Proventos", use_container_width=True): dialog_consultar_proventos(ticker)
    with col_del:
        if st.button("Excluir Ativo", type="secondary", use_container_width=True):
            st.session_state.show_confirm_delete, st.session_state.delete_asset_id, st.session_state.delete_asset_ticker = True, asset_id, ticker
            st.rerun()
    with col_voltar:
        if st.button("Voltar", use_container_width=True):
            if current_type != 'Renda Fixa' and history_df.empty: db.delete_asset(asset_id, st.session_state.user_id)
            st.session_state.viewing_history, st.session_state.navigation_tab = None, "Visão Geral"
            st.session_state.table_key += 1
            st.rerun()

    # === ANÁLISE DE RENTABILIDADE (FASE 3: Ações, Fiis, Stocks, Reits, Cripto) ===
    supported_types = ['Ações', 'Fiis', 'ETF', 'Stocks', 'Reits', 'Cripto']
    if current_type in supported_types:
        st.session_state.last_ticker = ticker
        # Moeda definida no banco de dados (v1.2.1)
        is_usd_based = (asset_data['currency'] == 'USD')
        # Ativos tipo Stocks/Reits/Cripto SEMPRE buscam histórico USD do Yahoo Finance para o gráfico
        needs_market_history_usd = current_type in ['Stocks', 'Reits', 'Cripto']
        
        auth_key = f"auth_chart_{ticker}"
        
        st.markdown("---")
        st.markdown('<br>', unsafe_allow_html=True)
        st.markdown('<h3 style="color: #ffffff; text-align: center; margin-bottom: 20px;">Análise de Rentabilidade</h3>', unsafe_allow_html=True)
        
        # Estado Inicial: Exibir apenas o botão centralizado
        if not st.session_state.get(auth_key, False):
            # Usando colunas para centralizar o botão perfeitamente
            _, col_btn, _ = st.columns([1, 1, 1])
            with col_btn:
                if st.button("📊 Visualizar Rentabilidade vs CDI", type="primary", use_container_width=True, key=f"btn_auth_{ticker}"):
                    if is_usd_based:
                        usd_conversion_notice_dialog()
                    else:
                        st.session_state[auth_key] = True
                        st.rerun()
            return # Interrompe aqui até que seja autorizado
            
        # Se autorizado, processa e exibe o gráfico
        first_op_date = history_df['date'].min() if not history_df.empty else None
        
        if first_op_date:
            with st.spinner("Calculando rentabilidade..."):
                try:
                    import plotly.graph_objects as go
                    
                    # Ajuste do Ticker para Cripto no Yahoo Finance
                    fetch_ticker = get_crypto_ticker(ticker) if current_type == 'Cripto' else ticker
                    
                    # Buscar dados históricos
                    price_history = svc.get_asset_price_history(fetch_ticker, first_op_date)
                    cdi_factors = svc.get_daily_cdi_history(first_op_date)
                    # Histórico de câmbio é necessário se a moeda do registro for USD OU se for Cripto mas o registro for em BRL (para converter o preço de mercado USD para BRL)
                    needs_usd_history = is_usd_based or (current_type == 'Cripto' and asset_data['currency'] == 'BRL')
                    usd_history = svc.get_usd_brl_history(first_op_date) if needs_usd_history else pd.Series()
                    
                    if price_history.empty:
                        st.warning(f"Histórico de preços não disponível para {fetch_ticker}.")
                    elif cdi_factors.empty:
                        st.warning("Histórico do CDI não disponível no momento.")
                    elif is_usd_based and usd_history.empty:
                        st.warning("Histórico de câmbio não disponível para conversão.")
                    else:
                        # Preparar DataFrame temporal
                        start_dt = pd.to_datetime(first_op_date).tz_localize(None)
                        end_dt = pd.to_datetime("today").tz_localize(None)
                        all_dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
                        
                        df_chart = pd.DataFrame(index=all_dates)
                        
                        # Preço e Câmbio (Normalização de Timezone)
                        price_history.index = pd.to_datetime(price_history.index).tz_localize(None)
                        df_chart['price_native'] = price_history
                        df_chart['price_native'] = df_chart['price_native'].ffill()
                        
                        if needs_usd_history:
                            usd_history.index = pd.to_datetime(usd_history.index).tz_localize(None)
                            df_chart['usd_rate'] = usd_history
                            df_chart['usd_rate'] = df_chart['usd_rate'].ffill()
                            df_chart['price_brl'] = df_chart['price_native'] * df_chart['usd_rate']
                        else:
                            df_chart['price_brl'] = df_chart['price_native']
                            
                        # Normalização da Base (v1.2.1) - Garante que o gráfico comece em 0%
                        # Ajustando o preço de mercado inicial para coincidir com o preço de custo nominal do usuário
                        if not df_chart.empty and not history_df.empty:
                            # [v1.2.6] Garantir que pegamos a PRIMEIRA compra cronológica para normalização
                            temp_hist_sorted = history_df.sort_values('date', ascending=True)
                            first_market_price = df_chart['price_brl'].iloc[0]
                            first_purchase_price = temp_hist_sorted.iloc[0]['unit_price']
                            
                            # Se for ativo em USD, converte o preço nominal da primeira compra para BRL usando a taxa do primeiro dia
                            if asset_data['currency'] == 'USD' and 'usd_rate' in df_chart.columns:
                                first_purchase_price *= df_chart['usd_rate'].iloc[0]
                            
                            if first_market_price > 0:
                                norm_factor = first_purchase_price / first_market_price
                                df_chart['price_brl'] = df_chart['price_brl'] * norm_factor
                        
                        # CDI Acumulado
                        cdi_factors.index = pd.to_datetime(cdi_factors.index).tz_localize(None)
                        df_chart['cdi_factor'] = cdi_factors
                        df_chart['cdi_factor'] = df_chart['cdi_factor'].fillna(1.0) 
                        df_chart['cdi_cum'] = (df_chart['cdi_factor'].cumprod() - 1) * 100
                        
                        # Processar Rentabilidade Diária da Posição
                        hist_for_calc = history_df.copy()
                        hist_for_calc['date'] = pd.to_datetime(hist_for_calc['date']).dt.tz_localize(None)
                        
                        proventos_df = db.get_proventos(st.session_state.user_id)
                        proventos_df = proventos_df[proventos_df['ticker'] == ticker].copy()
                        
                        def get_prov_date(row):
                            return pd.Timestamp(year=int(row['ano'] or 2000), month=int(row['mes'] or 1), day=15)
                        
                        if not proventos_df.empty:
                            proventos_df['date'] = proventos_df.apply(get_prov_date, axis=1)
                        
                        daily_qty, daily_cost_brl, daily_prov_cum_brl = [], [], []
                        curr_qty, curr_cost_brl, curr_prov_cum_brl = 0.0, 0.0, 0.0
                        
                        ops_grouped = hist_for_calc.groupby('date')
                        prov_grouped = proventos_df.groupby('date')['valor'].sum() if not proventos_df.empty else pd.Series(dtype=float)

                        for date in all_dates:
                            if date in ops_grouped.groups:
                                for _, op in ops_grouped.get_group(date).iterrows():
                                    if op['quantity'] > 0: # Compra
                                        # Se o registro é em USD, converte custo para BRL usando o câmbio da época
                                        rate = df_chart.loc[date, 'usd_rate'] if is_usd_based and date in df_chart.index else 1.0
                                        if pd.isna(rate): rate = 1.0
                                        curr_qty += op['quantity']
                                        curr_cost_brl += op['quantity'] * op['unit_price'] * rate
                                    else: # Venda
                                        if curr_qty > 0:
                                            avg_p_brl = curr_cost_brl / curr_qty
                                            curr_cost_brl += op['quantity'] * avg_p_brl
                                        curr_qty += op['quantity']
                            
                            if date in prov_grouped.index:
                                curr_prov_cum_brl += prov_grouped[date]
                            
                            daily_qty.append(curr_qty)
                            daily_cost_brl.append(curr_cost_brl)
                            daily_prov_cum_brl.append(curr_prov_cum_brl)
                            
                        df_chart['qty'] = daily_qty
                        df_chart['cost_brl'] = daily_cost_brl
                        df_chart['prov_cum_brl'] = daily_prov_cum_brl
                        df_chart['market_value_brl'] = df_chart['qty'] * df_chart['price_brl']
                        
                        def calc_profit(row):
                            if row['cost_brl'] <= 1.0: return 0.0
                            return ((row['market_value_brl'] + row['prov_cum_brl']) / row['cost_brl'] - 1) * 100

                        df_chart['profit_pct'] = df_chart.apply(calc_profit, axis=1)
                        
                        # Plotar Gráfico
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['profit_pct'], mode='lines', name=display_ticker, line=dict(color='#00CC96', width=2.5), hovertemplate="%{y:.2f}%"))
                        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['cdi_cum'], mode='lines', name='CDI', line=dict(color='#636EFA', width=1.5, dash='dot'), hovertemplate="%{y:.2f}%"))
                        
                        fig.update_layout(
                            hovermode='x unified', template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            height=350, margin=dict(l=10, r=10, t=10, b=10),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            yaxis=dict(title='Rentabilidade (%)', gridcolor='rgba(255,255,255,0.05)'),
                            xaxis=dict(gridcolor='rgba(255,255,255,0.05)')
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        st.markdown("---")
                        st.info("💡 **Informação**: Os dados de rentabilidade do ativo levam em consideração os proventos recebidos no período.")

                except Exception as e:
                    st.error(f"Erro ao processar gráfico: {e}")
        else:
            st.info("Adicione sua primeira operação para visualizar o gráfico de rentabilidade.")
