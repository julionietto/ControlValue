import streamlit as st
import base64
import pandas as pd
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
@st.dialog("Confirmar Exclusão")
def confirm_delete_dialog(asset_id, ticker):
    st.warning(f"Tem certeza que deseja excluir o ativo **{format_ticker_for_display(ticker)}**?")
    st.write("Esta ação não poderá ser desfeita.")
    
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Confirmar Exclusão", type="primary", use_container_width=True):
            db.delete_asset(asset_id, st.session_state.user_id)
            st.session_state.viewing_history = None
            st.session_state.table_key += 1
            st.success("Ativo removido!")
            st.rerun()
    with col_no:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.show_confirm_delete = False
            st.rerun()

@st.dialog("Confirmar Exclusão de Operação")
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

@st.dialog("Adicionar novo ativo")
def dialog_adicionar_novo_ativo():
    categoria = st.radio("Selecione a Categoria", ["Renda Variável", "Renda Fixa"], horizontal=True)
    nome = st.text_input("Nome do Ativo")
    
    if categoria == "Renda Fixa":
        saldo = st.number_input("Saldo Atualizado (R$)", min_value=0.0, format="%.2f")
        st.markdown("")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirmar", type="primary", use_container_width=True):
                if nome:
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
                        except Exception:
                            pass
                        
                        if live_native <= 0.0:
                            st.error(f"É possível que o ativo informado ('{clean_name}') não exista. Por favor, digite o código do ativo novamente.")
                            st.stop()
                            
                    # Adiciona ou recupera o ativo
                    db.add_empty_asset(clean_name, tipo_inicial, st.session_state.user_id)
                    
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
                                'fair_value': row[6]
                            }
                            
                            if tipo_inicial != 'Renda Fixa':
                                asset_data['original_current_price'] = live_native
                                asset_data['current_price'] = live_brl

                            st.session_state.viewing_history = asset_data
                            st.rerun()
                else:
                    st.error("Informe o nome do ativo.")
        with col2:
            if st.button("Cancelar", use_container_width=True):
                st.rerun()




def show_asset_details_screen(asset_data):
    asset_id = asset_data['id']
    ticker = asset_data['ticker']
    display_ticker = format_ticker_for_display(ticker)
    current_type = asset_data['asset_type']

    @st.dialog("Adicionar Operação")
    def dialog_add_operation():
        st.markdown(f"**Ativo:** `{display_ticker}`")
        st.markdown("---")
        
        op_type = st.radio("Tipo de Operação", ["Compra", "Venda"], horizontal=True, key="add_op_type")
        op_date = st.date_input("Data", value=pd.Timestamp.now().date(), max_value=pd.Timestamp.now().date(), format="DD/MM/YYYY", key="add_op_date")
        
        if current_type in ['Ações', 'Fiis', 'Stocks', 'Reits']:
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

    @st.dialog("Editar Operação")
    def dialog_edit_operation(op_data):
        st.markdown(f"**Editando Operação - Ativo:** `{display_ticker}`")
        st.markdown("---")
        
        try:
            current_date_obj = pd.to_datetime(op_data['date']).date()
        except:
            current_date_obj = pd.Timestamp.now().date()
            
        op_type = st.radio("Tipo de Operação", ["Compra", "Venda"], index=0 if op_data['quantity'] >= 0 else 1, horizontal=True, key=f"edit_op_type_{op_data['id']}")
        op_date = st.date_input("Data", value=current_date_obj, max_value=pd.Timestamp.now().date(), format="DD/MM/YYYY", key=f"edit_op_date_{op_data['id']}")
        
        initial_qty = abs(op_data['quantity'])
        if current_type in ['Ações', 'Fiis', 'Stocks', 'Reits']:
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
                # Usa asset_id do op_data ou do escopo, mas op_data é mais seguro
                target_asset_id = op_data['asset_id'] if 'asset_id' in op_data else asset_id
                db.update_asset_operation(op_data['id'], target_asset_id, st.session_state.user_id, op_date.strftime("%Y-%m-%d"), final_qty, op_price)
                st.session_state.viewing_history = db.get_asset_by_id(target_asset_id, st.session_state.user_id) # Atualiza dados do ativo no estado
                st.success("Operação atualizada!")
                st.rerun()
        with col_c2:
            if st.button("Excluir", type="secondary", use_container_width=True, key=f"delete_op_{op_data['id']}"):
                st.session_state.show_confirm_delete_op = True
                st.session_state.op_to_delete = op_data.to_dict() # Converte para dict para garantir persistência
                st.rerun()
        with col_c3:
            if st.button("Cancelar", use_container_width=True, key=f"cancel_edit_{op_data['id']}"):
                st.rerun()

    asset_id = asset_data['id']
    ticker = asset_data['ticker']
    display_ticker = format_ticker_for_display(ticker)
    current_type = asset_data['asset_type']
    
    # Verifica se deve abrir os diálogos de confirmação (No início para garantir precedência)
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
    if current_type == 'Renda Fixa':
        init_guidance = "COMPRA"
    else:
        init_guidance = "COMPRA" if compare_init <= price_ceiling else "AGUARDE"
    
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f'<h2 style="color: #ffffff; margin-top: 0;">Detalhe do Ativo: {escape_html(display_ticker)}</h2>', unsafe_allow_html=True)

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
            if current_type in foreign_types:
                return val * usd_to_brl_rate
            return val

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
            if "," in formatted:
                formatted = formatted.rstrip('0').rstrip(',')
            return formatted
        return f"{qty:,.0f}".replace(",", ".")

    def format_details_val(val, show_symbol=True):
        fmt = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        if not show_symbol: return fmt
        return f"{display_symbol} {fmt}"

    if is_us_asset:
        # Para Stocks e Reits, usamos valores nativos (USD) na tela de detalhes
        total_investido_native = (history_df['quantity'] * history_df['unit_price']).sum() if not history_df.empty else 0.0
        total_ativo_native = (history_df['quantity'] * price_now_native).sum() if not history_df.empty else (total_qtd * price_now_native)
        retorno_total_native = total_ativo_native - total_investido_native
        
        # Converte proventos (em BRL) para USD para exibição
        total_proventos_usd = total_proventos / usd_to_brl_rate if usd_to_brl_rate > 0 else 0.0
        
        retorno_total_com_prov_native = retorno_total_native + total_proventos_usd
        retorno_total_pct = (retorno_total_com_prov_native / total_investido_native * 100) if total_investido_native > 0 else 0.0
        yield_on_cost = (total_proventos_usd / total_investido_native * 100) if total_investido_native > 0 else 0.0
        
        # Labels para cards
        card_investido = format_details_val(total_investido_native)
        card_ativo = format_details_val(total_ativo_native)
        card_proventos = format_details_val(total_proventos_usd)
        card_retorno = format_details_val(retorno_total_com_prov_native)
    else:
        # Para outros ativos (Ações, Fiis, Cripto), mantemos BRL
        retorno_total_com_prov = retorno_total + total_proventos
        retorno_total_pct = (retorno_total_com_prov / total_investido * 100) if total_investido > 0 else 0.0
        yield_on_cost = (total_proventos / total_investido * 100) if total_investido > 0 else 0.0
        
        card_investido = format_brl(total_investido)
        card_ativo = format_brl(total_ativo)
        card_proventos = format_brl(total_proventos)
        card_retorno = format_brl(retorno_total_com_prov)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1: create_card("Total Investido", card_investido)
    with col2: create_card("Total do Ativo", card_ativo)
    with col3: create_card("Total de Proventos", card_proventos)
    
    ret_delta = f"{retorno_total_pct:,.2f}%".replace('.', ',')
    with col4: create_card("Retorno Total", card_retorno, ret_delta)
    
    yoc_formatted = f"{yield_on_cost:,.2f}%".replace('.', ',')
    with col5: create_card("Yeld On Cost", yoc_formatted)
    
    with col6: create_card("Quantidade Total", format_qty_hist(total_qtd, current_type))
    
    st.markdown("---")
    
    col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)
    currency_symbol = "$" if current_type in ['Stocks', 'Reits'] else "R$"
    
    with col_p1:
        asset_types = ["Ações", "Fiis", "Cripto", "Reits", "Stocks", "Renda Fixa"]
        try:
            type_idx = asset_types.index(current_type)
        except ValueError:
            type_idx = 0
        is_disabled = (current_type == 'Renda Fixa')
        new_asset_type = st.selectbox("Tipo de Ativo", asset_types, index=type_idx, disabled=is_disabled)

    if current_type == 'Cripto':
        display_val, display_sym = price_now_brl, "R$"
    elif current_type in ['Stocks', 'Reits']:
        display_val, display_sym = price_now_native, "$"
    else:
        display_val, display_sym = price_now_native, "R$"
    
    with col_p2:
        if current_type == 'Renda Fixa':
            new_avg_price = st.number_input("Saldo Acumulado (R$)", min_value=0.0, format="%.2f", value=float(avg_price_native))
        else:
            formatted_avg = f"{currency_symbol} {avg_price_native:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            st.text_input("Preço Médio", value=formatted_avg, disabled=True)
            new_avg_price = asset_data.get('average_price', 0.0)
            
    with col_p3:
        if current_type == 'Renda Fixa':
            new_price_ceiling = st.number_input(f"Preço Teto ({currency_symbol})", min_value=0.0, format="%.2f", value=float(price_ceiling), disabled=True)
        else:
            new_price_ceiling = st.number_input(f"Preço Teto ({currency_symbol})", min_value=0.0, format="%.2f", value=float(price_ceiling))
    
    with col_p4:
        if current_type == 'Renda Fixa':
            new_fair_value = st.number_input(f"Preço Justo ({currency_symbol})", min_value=0.0, format="%.2f", value=float(fair_value), disabled=True)
        else:
            new_fair_value = st.number_input(f"Preço Justo ({currency_symbol})", min_value=0.0, format="%.2f", value=float(fair_value))
        
    with col_p5:
        if current_type == 'Renda Fixa':
            st.text_input("Cotação Atual", value="R$ 0,00", disabled=True)
        else:
            formatted_price = f"{display_sym} {display_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            st.text_input("Cotação Atual", value=formatted_price, disabled=True)
        
    if current_type != 'Renda Fixa':
        new_guidance = "COMPRA" if compare_init <= new_price_ceiling else "AGUARDE"
        if new_guidance != init_guidance:
            st.info(f"Nova Orientação baseado no Preço Teto: **{new_guidance}**")
            
    if st.button("Salvar", type="primary", use_container_width=False):
        if current_type != 'Renda Fixa' and history_df.empty:
            st.error("É necessário adicionar pelo menos uma operação antes de salvar o ativo.")
        else:
            db.update_asset(
                asset_id, 
                st.session_state.user_id,
                ticker, 
                new_asset_type, 
                asset_data.get('quantity', 0.0), 
                new_avg_price, 
                new_price_ceiling, 
                new_fair_value
            )
            st.session_state.viewing_history = None
            st.session_state.table_key += 1
            st.success("Alterações salvas com sucesso!")
            st.rerun()
            
    st.markdown("---")
    
    if history_df.empty:
        st.warning("Nenhum registro de operação encontrado para este ativo.")
    else:
        display_hist = pd.DataFrame()
        display_hist['Data'] = pd.to_datetime(history_df['date']).dt.strftime('%d/%m/%Y')
        display_hist['Qtd'] = history_df.apply(lambda x: format_qty_hist(x['quantity'], current_type), axis=1)
        
        if is_us_asset:
            # Mostra valores nativos em USD
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
        
        display_hist = display_hist.reset_index()
        display_hist.rename(columns={'index': 'op_idx'}, inplace=True)
        
        # Alinhamentos via Style
        styled_hist = display_hist.style.set_properties(**{'text-align': 'center'}, subset=['Data', 'Qtd']) \
                                       .set_properties(**{'text-align': 'right'}, subset=['Preço', 'Valor Operação', '% Ganho', 'Vlr Atualizado', 'Lucro/Prej'])
        
        selected_op = st.dataframe(
            styled_hist, 
            hide_index=True, 
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "op_idx": None  # Oculta a coluna op_idx
            },
            key=f"history_df_{asset_id}_{st.session_state.refresh_id}"
        )

        if selected_op.selection.rows:
            row_idx = selected_op.selection.rows[0]
            if row_idx < len(history_df):
                op_to_edit = history_df.iloc[row_idx]
                dialog_edit_operation(op_to_edit)

    st.markdown("---")
    
    col_add, col_del, col_voltar = st.columns(3)
    
    with col_add:
        if current_type != 'Renda Fixa':
            if st.button("Adicionar Operação", type="primary", use_container_width=True):
                dialog_add_operation()
    
    with col_del:
        if st.button("Excluir Ativo", type="secondary", use_container_width=True):
            st.session_state.show_confirm_delete = True
            st.session_state.delete_asset_id = asset_id
            st.session_state.delete_asset_ticker = ticker
            st.rerun()
            
    with col_voltar:
        if st.button("Voltar", use_container_width=True):
            if current_type != 'Renda Fixa' and history_df.empty:
                db.delete_asset(asset_id, st.session_state.user_id)
            st.session_state.viewing_history = None
            st.session_state.table_key += 1
            st.rerun()

    # Os triggers de diálogo foram movidos para dentro de show_asset_details_screen e áreas de fluxo

# Inicializa o banco de dados

def render_visao_geral_view():
    # Renderiza Visão Geral
    st.markdown('<h2 style="color: #ffffff; font-size: 1.5rem; margin-bottom: 1.5rem;">Visão Geral</h2>', unsafe_allow_html=True)

    assets_df = db.get_all_assets(st.session_state.user_id)

    if st.session_state.viewing_history:
        # Mostra a tela combinada de Dados do Ativo e Registro de Operações
        show_asset_details_screen(st.session_state.viewing_history)
        st.stop()

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

        final_tickers_to_fetch = []
        for t in tickers_br:
            if m_status['BR'] or is_first_load or t not in st.session_state.price_cache:
                final_tickers_to_fetch.append(t)
        
        for t in tickers_us:
            if m_status['US'] or is_first_load or t not in st.session_state.price_cache:
                final_tickers_to_fetch.append(t)
                
        for t in tickers_crypto:
            if m_status['CRYPTO'] or t not in st.session_state.price_cache: # Bitcoin sempre entra
                final_tickers_to_fetch.append(t)

        with st.spinner("Buscando preços atualizados..."):
            refresh_id = st.session_state.refresh_id
            
            # Só chama a API para o que o mercado permitir (ou se for a primeira carga)
            if final_tickers_to_fetch:
                new_prices = svc.fetch_current_prices(final_tickers_to_fetch, refresh_id)
                st.session_state.price_cache.update(new_prices)
            
            # O current_prices final é a união do que acabamos de buscar com o que já tínhamos no cache
            current_prices = st.session_state.price_cache

            # Prepara dados e verifica se é Auto-Refresh
            current_datarefresh = st.session_state.get('datarefresh', 0)
            is_auto_refresh = False
            if 'last_datarefresh' not in st.session_state:
                st.session_state.last_datarefresh = current_datarefresh
                is_auto_refresh = True
            elif current_datarefresh != st.session_state.last_datarefresh:
                st.session_state.last_datarefresh = current_datarefresh
                is_auto_refresh = True
                
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
            types_to_convert = foreign_market_types if is_market_price else foreign_input_types
            if row['asset_type'] in types_to_convert:
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
                
            foreign_types = ['Stocks', 'Reits']
            def convert_to_brl(val):
                if row['asset_type'] in foreign_types:
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
        
        # Busca todos os proventos globais
        global_total_proventos = db.get_all_total_proventos(st.session_state.user_id)
        
        # Retorno Total = Lucro/Prejuízo + Proventos Globais
        total_profit_loss = assets_df['profit_loss'].sum() + global_total_proventos
        total_profit_loss_pct = (total_profit_loss / total_invested * 100) if total_invested > 0 else 0
        
        total_renda_fixa = assets_df[assets_df['asset_type'] == 'Renda Fixa']['current_value'].sum()
        total_renda_variavel = assets_df[assets_df['asset_type'] != 'Renda Fixa']['current_value'].sum()
        
        # Calcular o total de ações/FIIs/Reits/Stocks (ignora Cripto e Renda Fixa)
        tipos_acoes = ['Ações', 'Fiis', 'Stocks', 'Reits']
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
        st.markdown('<h3 style="text-align: center; color: #ffffff; margin-bottom: 1.5rem;">Meus Ativos</h3>', unsafe_allow_html=True)
        
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
        st.subheader("Ativos Consolidados")
        
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
                'Peso %': asset['weight_pct']
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
            if row['Tipo'] in ['Stocks', 'Reits', 'Cripto']:
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
                                         .set_properties(**{'text-align': 'right'}, subset=['Cotação Atual', 'Valor atualizado', 'Peso %'])
        
        st.markdown('<div style="font-size: 0.85rem; color: #a1a1aa; margin-bottom: 5px; margin-left: 2px;">✏️ Editar</div>', unsafe_allow_html=True)
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
            st.rerun()
    
        # Botão Adicionar novo ativo
        st.markdown("")
        if st.button("Adicionar novo ativo", type="primary", use_container_width=False):
            dialog_adicionar_novo_ativo()
    
        st.markdown("---")
    
        # --- SEÇÃO RADAR ---
        st.markdown('<h2 style="text-align: center; color: #ffffff; margin-top: 2rem; margin-bottom: 2rem;">Balanceamento e Diversificação</h2>', unsafe_allow_html=True)
    
        def show_radar_table(title, asset_types, df):
            st.subheader(title)
            radar_df = df[df['asset_type'].isin(asset_types)].copy()
            
            if not radar_df.empty:
                # Ordena por valor total do ativo na carteira de forma crescente
                radar_df = radar_df.sort_values(by='current_value', ascending=True)
                # Calcula a diferença entre a linha atual e a anterior
                radar_df['diff_calculada'] = radar_df['current_value'].diff().fillna(0)
                
                # Prepara o dataframe de exibição
                display_radar = pd.DataFrame()
                display_radar['Ticker'] = radar_df['ticker'].apply(format_ticker_for_display)
                display_radar['Valor do Ativo'] = radar_df['current_value'].apply(format_brl_custom)
                display_radar['Diferença Ativo Anterior'] = radar_df['diff_calculada'].apply(format_brl_custom)
                
                # Alinhamentos via Style
                styled_radar = display_radar.style.set_properties(**{'text-align': 'center'}, subset=['Ticker']) \
                                                 .set_properties(**{'text-align': 'right'}, subset=['Valor do Ativo', 'Diferença Ativo Anterior'])
                
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
                show_radar_table("Ativos no Brasil", ['Ações', 'Fiis'], assets_df)
            with col_radar2:
                show_radar_table("Ativos nos Estados Unidos", ['Stocks', 'Reits'], assets_df)
        else:
            show_radar_table("Ativos no Brasil", ['Ações', 'Fiis'], assets_df)
    
    
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
                    fig_type = px.pie(assets_df, values='current_value', names='asset_type', title='Por Tipo de Ativo', hole=0.4)
                    st.plotly_chart(fig_type, use_container_width=True)
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
                    
                    # Fetch historical prices
                    price_history = {}
                    for t in tickers_port:
                        asset_row = all_assets_user[all_assets_user['ticker']==t]
                        if not asset_row.empty:
                            tyf = f"{t}-USD" if (asset_row['asset_type'].iloc[0]=='Cripto' and '-' not in t) else t
                            hist = svc.get_index_history(tyf, period="2y")
                            if not hist.empty:
                                # Normaliza timezone e hora
                                if hist.index.tz is not None:
                                    hist.index = hist.index.tz_localize(None)
                                hist.index = hist.index.normalize()
                                price_history[tyf] = hist
                    
                    usd_rate_hist = svc.get_index_history("BRL=X", period="2y")
                    if not usd_rate_hist.empty:
                        if usd_rate_hist.index.tz is not None:
                            usd_rate_hist.index = usd_rate_hist.index.tz_localize(None)
                        usd_rate_hist.index = usd_rate_hist.index.normalize()
                    
                    # Calcular valor do portfólio em cada fechamento de mês
                    portfolio_values = []
                    for dt in meses_fechamento:
                        total_dt = 0.0
                        for _, asset in all_assets_user.iterrows():
                            # Quantidade na data dt
                            history_asset = db.get_asset_history(asset['id'], st.session_state.user_id)
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
                                            
                                            # Conversão se necessário
                                            if asset['asset_type'] in ['Stocks', 'Reits', 'Cripto']:
                                                u_dates = usd_rate_hist.index[usd_rate_hist.index <= dt]
                                                rate = usd_rate_hist.loc[u_dates[-1]] if not u_dates.empty else usd_to_brl_rate
                                                p = p * rate
                                            
                                            total_dt += qty_at_dt * p
                            elif asset['asset_type'] == 'Renda Fixa':
                                total_dt += asset['average_price']
                        
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
                        # IPCA agora vem como Número Índice (432). Basta dividir pelo valor base.
                        full_range = pd.date_range(start=ipca_vals.index.min(), end=perf_df['Data'].max(), freq='D')
                        ipca_daily = ipca_vals.reindex(full_range).ffill().bfill()
                        ipca_resampled = ipca_daily.reindex(perf_df['Data']).ffill().bfill()
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
                st.plotly_chart(fig_sect, use_container_width=True)
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
                
                    all_prov_db = db.get_all_proventos(st.session_state.user_id)
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
                    fig_fii_sect = px.pie(
                        fii_assets, 
                        values='current_value', 
                        names='sector', 
                        title='Distribuição por Segmento', 
                        hole=0.4
                    )
                    st.plotly_chart(fig_fii_sect, use_container_width=True)
                with col_fii3:
                    fig_fii_class = px.pie(
                        chart_df, 
                        values='current_value', 
                        names='classe', 
                        title='Recebíveis x Tijolos', 
                        hole=0.4,
                        color='classe',
                        color_discrete_map={'Tijolo': '#00CC96', 'Recebíveis': '#636EFA'}
                    )
                    st.plotly_chart(fig_fii_class, use_container_width=True)
                
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
            all_prov_db = db.get_all_proventos(st.session_state.user_id)
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
                        except:
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
                    
                    fig_sint = px.bar(
                        resumo_sintetico,
                        x='ano',
                        y='vl_premio',
                        title='Total Anual de Prêmios Recebidos (R$)',
                        text_auto='.2f',
                        labels={'vl_premio': 'Total Prêmio (R$)', 'ano': 'Ano'}
                    )
                    
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
