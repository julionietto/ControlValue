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




@st.dialog("Confirmar Exclusão")
def confirm_delete_dialog(asset_id, ticker):
    st.warning(f"Tem certeza que deseja excluir o ativo **{format_ticker_for_display(ticker)}**?")
    st.write("Esta ação não poderá ser desfeita.")
    
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Confirmar Exclusão", type="primary", use_container_width=True):
            db.delete_asset(asset_id, st.session_state.user_id)
            st.session_state.refresh_id += 1
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
            st.session_state.refresh_id += 1
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
                    st.session_state.refresh_id += 1
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
                        cursor.execute("SELECT * FROM assets WHERE ticker = ? AND user_id = ?", (clean_name, st.session_state.user_id))
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
                            st.session_state.refresh_id += 1
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
                st.session_state.refresh_id += 1
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
                st.session_state.refresh_id += 1
                st.session_state.viewing_history = db.get_asset_by_id(target_asset_id, st.session_state.user_id) # Atualiza dados do ativo no estado
                st.success("Operação atualizada!")
                st.rerun()
        with col_c2:
            if st.button("Excluir", type="secondary", use_container_width=True, key=f"delete_op_{op_data['id']}"):
                st.session_state.show_confirm_delete_op = True
                st.session_state.op_to_delete = op_data.to_dict() # Converte para dict para garantir persistência
                st.session_state.refresh_id += 1 # Reset selection do dataframe
                st.rerun()
        with col_c3:
            if st.button("Cancelar", use_container_width=True, key=f"cancel_edit_{op_data['id']}"):
                st.session_state.refresh_id += 1 # Reset selection do dataframe
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
            st.session_state.refresh_id += 1
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
db.init_db()

st.set_page_config(page_title="Ativos Financeiros", page_icon="📈", layout="wide")

# Injeção de CSS personalizado
import os
style_path = os.path.join(os.path.dirname(__file__), "style.css")
if os.path.exists(style_path):
    with open(style_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Lógica de Autenticação
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'table_key' not in st.session_state:
    st.session_state.table_key = 0

@st.dialog("Criar Conta")
def dialog_register_user():
    st.markdown("### 📝 Cadastre-se")
    reg_username = st.text_input("Nome de Usuário", placeholder="Como quer ser chamado")
    reg_email = st.text_input("Email", placeholder="seu@email.com")
    reg_birth = st.date_input("Data de Nascimento", min_value=pd.to_datetime('1900-01-01').date(), max_value=pd.to_datetime('today').date(), format="DD/MM/YYYY")
    reg_pass = st.text_input("Senha", type="password", placeholder="Sua senha")
    reg_confirm = st.text_input("Confirmar Senha", type="password", placeholder="Repita a senha")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Criar Conta", type="primary", use_container_width=True):
            if reg_username and reg_email and reg_pass:
                if reg_pass == reg_confirm:
                    db.create_user(reg_username, reg_email, reg_birth.strftime("%Y-%m-%d"), reg_pass)
                    st.success("Conta criada com sucesso! Faça login.")
                    st.rerun()
                else:
                    st.error("As senhas não conferem.")
            else:
                st.error("Preencha todos os campos obrigatórios.")
    close_login_dialog = False
    with col2:
        if st.button("Cancelar", use_container_width=True):
            close_login_dialog = True
            
    if close_login_dialog:
        st.rerun()

if not st.session_state.authenticated:
    # Centraliza o login usando colunas [15%, 70%, 15%]
    _, login_col, _ = st.columns([0.15, 0.7, 0.15])
    
    with login_col:
        # Usamos um container com borda para criar o efeito de card de forma nativa e limpa
        with st.container(border=True):
            col_logo, col_form = st.columns([0.6, 0.4], gap="medium", vertical_alignment="bottom")
            
            with col_logo:
                st.image("images/logoInvestControl.png", use_container_width=True)
                
            with col_form:
                st.markdown('<h1 style="text-align: left; margin-top: 0; margin-bottom: 24px; font-size: 2.25rem; font-weight: 700; color: #ffffff;">🔐 Acesso</h1>', unsafe_allow_html=True)
                
                user_count = db.get_user_count()
                
                if user_count == 0:
                    st.info("Nenhum usuário cadastrado. Crie sua conta de administrador.")
                    with st.form("register_form_admin"):
                        new_user = st.text_input("Usuário", value="admin", disabled=True)
                        new_email = st.text_input("Email", placeholder="seu@email.com")
                        new_birth = st.date_input("Data de Nascimento", format="DD/MM/YYYY")
                        new_pass = st.text_input("Senha", type="password", placeholder="Sua senha")
                        confirm_pass = st.text_input("Confirmar", type="password", placeholder="Repita a senha")
                        submit_reg = st.form_submit_button("Criar Conta de Admin", use_container_width=True)
                    
                    if submit_reg:
                        if new_user and new_email and new_pass:
                            if new_pass == confirm_pass:
                                db.create_user(new_user, new_email, new_birth.strftime("%Y-%m-%d"), new_pass)
                                success, uid, uname = db.verify_user(new_user, new_pass)
                                if success:
                                    st.session_state.authenticated = True
                                    st.session_state.user_id = uid
                                    st.session_state.username = uname
                                    st.session_state.is_admin = True
                                    st.success("Administrador cadastrado!")
                                    st.rerun()
                            else:
                                st.error("As senhas não conferem.")
                        else:
                            st.error("Preencha todos os campos.")
                else:
                    with st.form("login_form"):
                        user_input = st.text_input("Email / Usuário", placeholder="seu@email.com")
                        password = st.text_input("Senha", type="password", placeholder="Sua senha")
                        submit_login = st.form_submit_button("Entrar", use_container_width=True)
                    
                    if submit_login:
                        success, uid, uname = db.verify_user(user_input, password)
                        if success:
                            st.session_state.authenticated = True
                            st.session_state.user_id = uid
                            st.session_state.username = uname
                            st.session_state.is_admin = (uname == 'admin')
                            st.rerun()
                        else:
                            st.error("Usuário ou senha incorretos.")
                
            # Link para criar conta se não for admin: posicionado abaixo das colunas para manter o alinhamento do logo com o botão Entrar
            if user_count > 0:
                st.markdown('<div style="margin-top: 12px;"></div>', unsafe_allow_html=True)
                if st.button("Não tem conta? Criar conta", use_container_width=True):
                    dialog_register_user()
    st.stop()


# Inicializar variáveis de controle no session_state para limpar o form
if 'form_ticker' not in st.session_state:
    st.session_state.form_ticker = ""
if 'form_avg_price' not in st.session_state:
    st.session_state.form_avg_price = 0.01
if 'form_rf_saldo' not in st.session_state:
    st.session_state.form_rf_saldo = 0.01
if 'needs_clear' not in st.session_state:
    st.session_state.needs_clear = False
if 'refresh_id' not in st.session_state:
    st.session_state.refresh_id = 0
if 'show_confirm_delete' not in st.session_state:
    st.session_state.show_confirm_delete = False
if 'delete_asset_info' not in st.session_state:
    st.session_state.delete_asset_info = None
if 'viewing_history' not in st.session_state:
    st.session_state.viewing_history = None # Armazena os dados do ativo sendo visualizado

# Atualização automática a cada 5 minutos (300.000 ms)
st_autorefresh(interval=300000, key="datarefresh")



# ==============================
# MENU DE PERFIL
# ==============================





# Dispara os diálogos de forma segura por fora do popover para que funcionem bem após recriação
if st.session_state.pop('trigger_dialog_ativos', False):
    dialog_importar_ativos()
if st.session_state.pop('trigger_dialog_proventos', False):
    dialog_importar_proventos()
if st.session_state.pop('trigger_dialog_perfil', False):
    dialog_user_profile()


# ==============================
# ADMIN DASHBOARD
# ==============================
if st.session_state.get('is_admin', False):
    render_top_header("🛡️ Painel de Administração", "Gestão de usuários do sistema.")
    
    # 1. Metricas
    users_df = db.get_all_users()
    if 'created_at' in users_df.columns:
        users_df['created_at_dt'] = pd.to_datetime(users_df['created_at'], errors='coerce')
        users_df['created_at'] = users_df['created_at_dt'].dt.strftime('%d/%m/%Y')
    total_users = len(users_df)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'''
        <div class="metric-card">
            <div class="metric-title">Total de Usuários</div>
            <div class="metric-value">{total_users}</div>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('<br>', unsafe_allow_html=True)
    
    # 2. Cadastro
    if st.button("➕ Novo Usuário", type="primary"):
        st.session_state.show_add_user = True
        
    @st.dialog("Criar Novo Usuário")
    def dialog_add_user():
        new_username = st.text_input("Usuário")
        new_email = st.text_input("Email")
        new_birth = st.date_input("Data de Nascimento", format="DD/MM/YYYY")
        new_password = st.text_input("Senha", type="password")
        if st.button("Salvar", use_container_width=True):
            if new_username and new_email and new_password:
                db.admin_create_user(new_username, new_email, new_birth.strftime("%Y-%m-%d"), new_password)
                st.success("Criado com sucesso!")
                st.session_state.show_add_user = False
                st.rerun()
            else:
                st.error("Preencha todos os campos obrigatórios.")
                
    if st.session_state.get('show_add_user', False):
        dialog_add_user()
        
    # 3. Tabela
    if not users_df.empty:
        # Reordena para mostrar Email e Nascimento
        display_users = users_df[['id', 'username', 'email', 'birth_date', 'created_at']].copy()
        # Formata a data de nascimento para dd/MM/yyyy
        display_users['birth_date'] = pd.to_datetime(display_users['birth_date'], errors='coerce').dt.strftime('%d/%m/%Y')
        display_users.columns = ['ID', 'Usuário', 'Email', 'Nascimento', 'Cadastro']
        
        st.dataframe(display_users, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="admin_users_table")
        if st.session_state.admin_users_table.selection.rows and not st.session_state.get('show_add_user', False):
            row_idx = st.session_state.admin_users_table.selection.rows[0]
            if row_idx < len(users_df):
                user_data_row = users_df.iloc[row_idx]
                
                @st.dialog("Editar / Excluir Usuário")
                def dialog_edit_user(u_data):
                    st.write(f"**ID:** {u_data['id']} | **Data de Cadastro:** {u_data['created_at']}")
                    edit_username = st.text_input("Usuário", value=u_data['username'])
                    edit_email = st.text_input("Email", value=u_data['email'] if u_data['email'] else "")
                    
                    try:
                        def_birth = pd.to_datetime(u_data['birth_date']).date() if u_data['birth_date'] else pd.to_datetime('2000-01-01').date()
                    except:
                        def_birth = pd.to_datetime('2000-01-01').date()
                        
                    edit_birth = st.date_input("Data de Nascimento", value=def_birth, min_value=pd.to_datetime('1900-01-01').date(), max_value=pd.to_datetime('today').date(), format="DD/MM/YYYY")
                    edit_password = st.text_input("Nova Senha (deixe em branco para não alterar)", type="password", placeholder="*** (Criptografada)")
                    
                    colA, colB = st.columns(2)
                    with colA:
                        if st.button("Atualizar", type="primary", use_container_width=True):
                            db.admin_update_user(int(u_data['id']), edit_username, edit_email, edit_birth.strftime("%Y-%m-%d"), edit_password if edit_password else None)
                            st.success("Dados atualizados com sucesso")
                            time.sleep(1)
                            st.rerun()
                    with colB:
                        if st.button("Excluir", type="secondary", use_container_width=True):
                            if u_data['username'] == 'admin':
                                st.error("O administrador principal não pode ser excluído.")
                            else:
                                db.admin_delete_user(int(u_data['id']))
                                st.success("Excluido com sucesso!")
                                time.sleep(1)
                                st.rerun()
                                
                dialog_edit_user(user_data_row)
            
    st.stop()
# ==============================
# Verifica e cria dashboard do próximo ano (Automated Task)
if 'rollover_checked' not in st.session_state:
    if db.check_and_create_next_year_dashboard(st.session_state.user_id):
        st.session_state.refresh_id += 1
    st.session_state.rollover_checked = True

# Lógica de limpeza adiada para evitar StreamlitAPIException
if st.session_state.needs_clear:
    st.session_state.form_ticker = ""
    st.session_state.needs_clear = False

def update_ticker():
    """Callback para tratar o ticker: maiúsculas, sem espaços e auto-sufixo .SA"""
    raw_ticker = st.session_state.form_ticker
    
    # Verifica se há um espaço ao final (intenção de ignorar o .SA)
    ignore_sa = raw_ticker.endswith(" ")
    
    # Remove espaços e converte para maiúsculas
    clean_ticker = raw_ticker.replace(" ", "").upper()
    
    # Aplica o sufixo .SA se tiver 4 ou mais caracteres, não tiver ponto e não for para ignorar
    if len(clean_ticker) >= 4 and "." not in clean_ticker and not ignore_sa:
        clean_ticker += ".SA"
        
    st.session_state.form_ticker = clean_ticker

# Top Header com Título e Logout
render_top_header("Ativos Financeiros", "Controle de investimentos e análise de performance em tempo real.")
# Pega a navegação inicial do estado (que é inicializada posteriormente, mas tratamos aqui)
current_view = st.session_state.get('navigation_tab', 'Visão Geral')

# Área Principal - Divisão de Telas Baseada na Seleção
# Área Principal - Divisão de Telas Baseada na Seleção
if current_view == "Proventos Recebidos":
    st.markdown('<h2 style="color: #ffffff; font-size: 1.5rem; margin-bottom: 1.5rem;">Proventos Recebidos</h2>', unsafe_allow_html=True)
    
    proventos_df = db.get_proventos(st.session_state.user_id)
    
    meses_ordem = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    # ---- Popup: Editar Provento ----
    @st.dialog("✏️ Editar Provento")
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
    @st.dialog("⚠️ Confirmar Exclusão")
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
    @st.dialog("➕ Adicionar Ativo")
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
                    # Assim toda edição posterior atuará alterando os registros já existentes
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
            icon_path = os.path.join(os.path.dirname(__file__), "growth_icon.png")
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
                
                # Alinhamentos via Style
                cols_right = [col for col in col_order]
                styled_df = display_df.style.set_properties(**{'text-align': 'center'}, subset=['Ativo']) \
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
                    st.rerun()

                # Footer: Total Mensal (tabela separada, sem checkbox)
                st.markdown("""
                    <style>
                    .growth-positive { color: #00CC96 !important; }
                    .growth-negative { color: #EF553B !important; }
                    th { font-weight: normal !important; font-size: 0.85rem; }
                    td { font-size: 0.85rem; }
                    </style>
                """, unsafe_allow_html=True)

                footer_rows = []
                # Linha TOTAL
                tm_row = {'Mês': 'TOTAL'}
                style_val = 'font-weight: normal; font-size: 0.85rem; text-align: right;'
                for col in col_order:
                    val_fmt = format_provento(totais_row[col])
                    tm_row[col] = f'<div style="{style_val}">{val_fmt}</div>'
                footer_rows.append(tm_row)
                
                # Linha Aumento de Proventos (Fórmula)
                # Apenas se não for o ano mais antigo
                ano_mais_antigo = min(anos_disponiveis)
                if ano > ano_mais_antigo:
                    prev_year = ano - 1
                    df_prev = proventos_df[proventos_df['ano'] == prev_year]
                    pivot_prev = df_prev.pivot_table(index='ticker', columns='mes', values='valor', aggfunc='sum').fillna(0)
                    for mes in meses_ordem:
                        if mes not in pivot_prev.columns:
                            pivot_prev[mes] = 0.0
                    
                    # Totais do ano anterior
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
                        
                        # Estilo normal para valores de meses e totais do rodapé
                        style_val = 'font-weight: normal; font-size: 0.85rem; text-align: right;'
                        
                        if val_prev > 0:
                            pct = ((val_curr / val_prev) - 1) * 100
                            color = "#00CC96" if pct >= 0 else "red"
                            growth_row[col] = f'<div style="color: {color}; {style_val}">{pct:,.2f}%</div>'.replace('.', ',')
                        else:
                            growth_row[col] = f'<div style="{style_val}">0,00%</div>'
                    footer_rows.append(growth_row)

                # Linha Média até Mês Corrente - APENAS PARA O ANO ATUAL
                if ano == ano_atual:
                    # Obter mês atual para cálculo da média
                    now = pd.Timestamp.now()
                    mes_atual_idx = now.month # 1 a 12
                    mes_atual_nome = meses_ordem[mes_atual_idx-1]
                    
                    avg_ytd_row = {'Mês': f'<div style="font-size: 0.8rem; white-space: nowrap;">Média até {mes_atual_nome}</div>'}
                    
                    # Soma Jan até Mês Atual
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

                # Ajuste de labels e fonte normal para valores
                import pandas as pd
                df_footer = pd.DataFrame(footer_rows)
                # Diminui fonte de 'Valor Mensal' no label (se possível via HTML fixo na célula)
                df_footer['Mês'] = df_footer['Mês'].replace('Valor Mensal', '<span style="font-size: 0.8rem;">Valor Mensal</span>')
                
                st.write(df_footer.to_html(escape=False, index=False), unsafe_allow_html=True)
                
                # Botão Adicionar Ativo apenas no ano atual
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
                # Formatação para exibição na tabela
                meses_cols = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                display_resumo = resumo_df.copy()
                for m in meses_cols:
                    display_resumo[m] = display_resumo[m].apply(format_provento)
                display_resumo['Valor Mensal'] = display_resumo['Valor Mensal'].apply(format_provento)
                display_resumo['Valor Anual'] = display_resumo['Valor Anual'].apply(format_provento)
                
                # Renomeia para exibição final de acordo com requests anteriores
                display_resumo.rename(columns={'Valor Anual': 'Valor Anual '}, inplace=True)
                
                cols_resumo = ['Ano'] + meses_cols + ['Valor Mensal', 'Valor Anual ']
                display_resumo = display_resumo[cols_resumo]

                # Identificar o maior valor global entre os meses (usando o df original numérico)
                global_max_val = resumo_df[meses_cols].values.max()

                def highlight_absolute_max(s):
                    if s.name in meses_cols:
                        # Precisamos pegar o valor numérico do resumo_df original para comparar
                        idx_s = s.index
                        res = []
                        for i in idx_s:
                            val_num = resumo_df.loc[i, s.name]
                            res.append('color: #00CC96' if (val_num == global_max_val and global_max_val > 0) else '')
                        return res
                    return ['' for _ in s]

                styled_resumo = display_resumo.style.apply(highlight_absolute_max, axis=0) \
                                              .set_properties(**{'text-align': 'center'}, subset=['Ano']) \
                                              .set_properties(**{'text-align': 'right'}, subset=meses_cols + ['Valor Mensal', 'Valor Anual '])

                st.dataframe(styled_resumo, hide_index=True, use_container_width=True)

                # ---- Tabela de Proventos Stocks e Reits ----
                assets_df_all = db.get_all_assets(st.session_state.user_id) # Note: this only returns qty > 0
                has_us_assets_active = not assets_df_all[assets_df_all['asset_type'].isin(['Stocks', 'Reits'])].empty

                if has_us_assets_active:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<h3 style="color: #ffffff; font-size: 1.2rem; margin-bottom: 1rem;">Proventos Recebidos de ativos dolarizados. (Valores em R$)</h3>', unsafe_allow_html=True)
                    
                    # To get types for all historical tickers, we need to check assets even with qty 0
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
                        
                        # Formatação
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
            
            # Select year
            ano_selecionado = st.selectbox("Selecione o Ano", anos_disponiveis, key="ano_ranking_prov")
            
            df_ano_ranking = proventos_df[proventos_df['ano'] == ano_selecionado].copy()
            
            if not df_ano_ranking.empty:
                ranking_df = df_ano_ranking.groupby('ticker')['valor'].sum().reset_index()
                ranking_df.rename(columns={'valor': 'Valor Anual', 'ticker': 'Ativo'}, inplace=True)
                ranking_df['Ativo'] = ranking_df['Ativo'].apply(format_ticker_for_display)
                ranking_df = ranking_df.sort_values(by='Valor Anual', ascending=False).reset_index(drop=True)
                ranking_df.index = ranking_df.index + 1
                ranking_df = ranking_df.reset_index().rename(columns={'index': 'Posição'})
                
                # Plotly Bar Chart Premium
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
                
                # Table format
                ranking_display = ranking_df.copy()
                ranking_display['Posição'] = ranking_display['Posição'].apply(lambda x: f"#{x}")
                ranking_display['Valor Anual'] = ranking_display['Valor Anual'].apply(lambda val: f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                
                styled_rank = ranking_display.style.set_properties(**{'text-align': 'center'}, subset=['Posição', 'Ativo'])                                                  .set_properties(**{'text-align': 'right'}, subset=['Valor Anual'])
                
                st.dataframe(styled_rank, hide_index=True, use_container_width=True)
            else:
                st.info(f"Nenhum provento registrado para o ano {ano_selecionado}.")

    st.stop()

if current_view == "Derivativos":
    st.markdown('<h2 style="color: #ffffff; font-size: 1.5rem; margin-bottom: 1.5rem;">Derivativos</h2>', unsafe_allow_html=True)
    
    @st.dialog("Editar Opção", width="large")
    def dialog_edit_opcao(op_data):
        st.markdown(f"### 📝 Editando Opção: `{format_ticker_for_display(op_data['ativo'])}`")
        
        st.markdown("#### 📊 Dados do Ativo")
        c1, c2, c3 = st.columns(3)
        with c1: ativo = st.text_input("Ativo", value=format_ticker_for_display(op_data['ativo']), disabled=True)
        with c2: cotacao_atual = st.number_input("Cotação Atual", value=float(op_data.get('Cotação Atual', 0.0)), disabled=True, format="%.2f")
        with c3: strike = st.number_input("Strike", min_value=0.01, step=0.01, value=float(op_data['strike']), format="%.2f")
        
        st.markdown("#### 📅 Prazos e Detalhes")
        c4, c5, c6, c7 = st.columns(4)
        with c4:
            try:
                dt_op_obj = pd.to_datetime(op_data['dt_operacao']).date()
            except:
                dt_op_obj = pd.Timestamp.now().date()
            dt_operacao = st.date_input("Dt Operação", value=dt_op_obj, format="DD/MM/YYYY")
        with c5:
            try:
                dt_venc_obj = pd.to_datetime(op_data['dt_vencimento']).date()
            except:
                dt_venc_obj = pd.Timestamp.now().date()
            dt_vencimento = st.date_input("Dt Vencimento", value=dt_venc_obj, format="DD/MM/YYYY")
        with c6:
            tp_opcao = st.selectbox("Tp Opção", ["CALL", "PUT"], index=0 if op_data['tp_opcao']=="CALL" else 1)
        with c7:
            derivativo = st.text_input("Derivativo", value=op_data['derivativo'])
            
        st.markdown("#### 💰 Valores e Posição")
        c8, c9, c10, c11 = st.columns(4)
        with c8:
            quantidade = st.number_input("Quantidade", value=int(op_data['quantidade']), step=100)
        with c9:
            vl_opcao = st.number_input("Vl Opção", min_value=0.00, step=0.01, value=float(op_data['vl_opcao']), format="%.2f")
        with c10:
            vl_premio_calc = vl_opcao * quantidade
            vl_premio = st.number_input("Vl Prêmio (Total)", value=float(vl_premio_calc), disabled=True, format="%.2f")
        with c11:
            status_opts = ["Aberta", "Encerrada", "Exercida"]
            status = st.selectbox("Status", status_opts, index=status_opts.index(op_data['status']) if op_data['status'] in status_opts else 0)

        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.session_state.get('confirm_zero_qtd_edit', False):
            st.warning("⚠️ A Quantidade está definida como ZERO. Tem certeza que deseja salvar?")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("Sim, salvar zerado", type="primary", use_container_width=True):
                    dt_op_str = dt_operacao.strftime("%Y-%m-%d")
                    dt_venc_str = dt_vencimento.strftime("%Y-%m-%d")
                    db.update_opcao(op_data['id'], st.session_state.user_id, ativo, strike, tp_opcao, dt_op_str, dt_venc_str, derivativo, quantidade, vl_opcao, vl_premio, status)
                    st.session_state['confirm_zero_qtd_edit'] = False
                    st.session_state.refresh_id += 1
                    st.success("Opção atualizada!")
                    st.rerun()
            with cc2:
                if st.button("Não, corrigir", use_container_width=True):
                    st.session_state['confirm_zero_qtd_edit'] = False
                    st.rerun()
        else:
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                if st.button("Salvar", type="primary", use_container_width=True):
                    if quantidade == 0:
                        st.session_state['confirm_zero_qtd_edit'] = True
                        st.rerun()
                    else:
                        dt_op_str = dt_operacao.strftime("%Y-%m-%d")
                        dt_venc_str = dt_vencimento.strftime("%Y-%m-%d")
                        db.update_opcao(op_data['id'], st.session_state.user_id, ativo, strike, tp_opcao, dt_op_str, dt_venc_str, derivativo, quantidade, vl_opcao, vl_premio, status)
                        st.session_state.refresh_id += 1
                        st.success("Opção atualizada!")
                        st.rerun()
            with col_c2:
                if st.button("Excluir", type="secondary", use_container_width=True):
                    st.session_state.show_confirm_delete_opcao = True
                    st.session_state.opcao_to_delete = op_data['id']
                    st.session_state.refresh_id += 1
                    st.rerun()
            with col_c3:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state.refresh_id += 1
                    st.rerun()

    @st.dialog("Confirmar Exclusão de Opção")
    def confirm_delete_opcao_dialog(opcao_id):
        st.warning("Tem certeza que deseja excluir esta opção?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Confirmar Exclusão", type="primary", use_container_width=True):
                db.delete_opcao(opcao_id, st.session_state.user_id)
                st.session_state.show_confirm_delete_opcao = False
                st.session_state.refresh_id += 1
                st.success("Opção excluída!")
                st.rerun()
        with col_no:
            if st.button("Cancelar", use_container_width=True):
                st.session_state.show_confirm_delete_opcao = False
                st.rerun()

    @st.dialog("Adicionar Opção", width="large")
    def dialog_add_opcao():
        st.markdown("### 🆕 Adicionar Nova Opção")
        
        st.markdown("#### 📊 Dados do Ativo")
        c1, c2, c3 = st.columns(3)
        with c1:
            ativo_input = st.text_input("Ativo (ex: PETR4)", key="add_opcao_ativo")
            ativo_val = ativo_input.strip().upper()
            if ativo_val and not ativo_val.endswith(".SA") and "." not in ativo_val:
                ativo_val += ".SA"
        with c2:
            cotacao_val = 0.0
            if len(ativo_val) >= 4:
                import services as svc
                prices = svc.fetch_current_prices([ativo_val], st.session_state.refresh_id)
                cotacao_val = prices.get(ativo_val, 0.0)
            st.number_input("Cotação Atual", value=float(cotacao_val), disabled=True, format="%.2f")
        with c3:
            strike = st.number_input("Strike", min_value=0.01, step=0.01, format="%.2f")
            
        st.markdown("#### 📅 Prazos e Detalhes")
        c4, c5, c6, c7 = st.columns(4)
        with c4:
            dt_operacao = st.date_input("Dt Operação", value=pd.Timestamp.now().date(), format="DD/MM/YYYY")
        with c5:
            dt_vencimento = st.date_input("Dt Vencimento", value=pd.Timestamp.now().date(), format="DD/MM/YYYY")
        with c6:
            tp_opcao = st.selectbox("Tp Opção", ["CALL", "PUT"])
        with c7:
            derivativo = st.text_input("Derivativo")
            
        st.markdown("#### 💰 Valores e Posição")
        c8, c9, c10, c11 = st.columns(4)
        with c8:
            quantidade = st.number_input("Quantidade", value=100, step=100)
        with c9:
            vl_opcao = st.number_input("Vl Opção", min_value=0.00, step=0.01, format="%.2f")
        with c10:
            vl_premio_calc = vl_opcao * quantidade
            vl_premio = st.number_input("Vl Prêmio (Total)", value=float(vl_premio_calc), disabled=True, format="%.2f")
        with c11:
            status = st.selectbox("Status", ["Aberta", "Encerrada", "Exercida"])

        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.session_state.get('confirm_zero_qtd_add', False):
            st.warning("⚠️ A Quantidade está definida como ZERO. Tem certeza que deseja salvar?")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("Sim, salvar zerado", type="primary", use_container_width=True):
                    dt_op_str = dt_operacao.strftime("%Y-%m-%d")
                    dt_venc_str = dt_vencimento.strftime("%Y-%m-%d")
                    db.insert_opcao(ativo_val, strike, tp_opcao, dt_op_str, dt_venc_str, derivativo, quantidade, vl_opcao, vl_premio, status, st.session_state.user_id)
                    st.session_state['confirm_zero_qtd_add'] = False
                    st.session_state.refresh_id += 1
                    st.success("Opção adicionada!")
                    st.rerun()
            with cc2:
                if st.button("Não, corrigir", use_container_width=True):
                    st.session_state['confirm_zero_qtd_add'] = False
                    st.rerun()
        else:
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                if st.button("Salvar", type="primary", use_container_width=True):
                    if ativo_val:
                        if quantidade == 0:
                            st.session_state['confirm_zero_qtd_add'] = True
                            st.rerun()
                        else:
                            dt_op_str = dt_operacao.strftime("%Y-%m-%d")
                            dt_venc_str = dt_vencimento.strftime("%Y-%m-%d")
                            db.insert_opcao(ativo_val, strike, tp_opcao, dt_op_str, dt_venc_str, derivativo, quantidade, vl_opcao, vl_premio, status, st.session_state.user_id)
                            st.session_state.refresh_id += 1
                            st.success("Opção adicionada!")
                            st.rerun()
                    else:
                        st.error("Informe o código do Ativo.")
            with col_c2:
                if st.button("Cancelar", use_container_width=True):
                    st.rerun()

    if st.session_state.get('show_confirm_delete_opcao', False):
        opcao_id_del = st.session_state.get('opcao_to_delete')
        confirm_delete_opcao_dialog(opcao_id_del)
        
    opcoes_df = db.get_opcoes(st.session_state.user_id)
    
    if opcoes_df.empty:
        st.info("Nenhum dado de Opções registrado. Por favor, importe o arquivo Opcoes.tsv no Menu de Perfil -> Importar Dados.")
        if st.button("Adicionar Opção", type="primary"):
            dialog_add_opcao()
    else:
        display_df = opcoes_df.copy()
        
        import services as svc
        tickers = display_df['ativo'].unique().tolist()
        prices_dict = svc.fetch_current_prices(tickers, st.session_state.refresh_id)
        display_df['Cotação Atual'] = display_df['ativo'].map(prices_dict).fillna(0.0)
        
        display_df['Diferença'] = display_df['Cotação Atual'] - display_df['strike']
        display_df['Taxa'] = display_df['vl_opcao'] / display_df['strike']
        display_df['Cobertura PUT'] = display_df['quantidade'] * display_df['strike']
        
        display_df['dt_operacao'] = pd.to_datetime(display_df['dt_operacao']).dt.strftime('%d/%m/%Y')
        display_df['dt_vencimento'] = pd.to_datetime(display_df['dt_vencimento']).dt.strftime('%d/%m/%Y')
        
        display_df['ativo'] = display_df['ativo'].apply(format_ticker_for_display)
        display_df.rename(columns={
            'ativo': 'Ativo',
            'strike': 'Strike',
            'tp_opcao': 'Tp Opção',
            'dt_operacao': 'Dt Operação',
            'dt_vencimento': 'Dt Vencimento',
            'derivativo': 'Derivativo',
            'quantidade': 'Quantidade',
            'vl_opcao': 'Vl Opção',
            'vl_premio': 'Vl Prêmio',
            'status': 'Status'
        }, inplace=True)
        
        ordem_colunas = [
            'id', 'Ativo', 'Cotação Atual', 'Strike', 'Diferença', 'Tp Opção', 
            'Dt Operação', 'Dt Vencimento', 'Derivativo', 'Quantidade', 
            'Vl Opção', 'Vl Prêmio', 'Taxa', 'Cobertura PUT', 'Status'
        ]
        display_df = display_df[ordem_colunas]
        
        # --- FILTROS ---
        st.markdown("### Filtros")
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)
        
        with fcol1:
            ativos_opts = ["Todos"] + sorted(display_df['Ativo'].unique().tolist())
            filt_ativo = st.selectbox("Ativo", ativos_opts)
        with fcol2:
            tp_opts = ["Todos"] + sorted(display_df['Tp Opção'].unique().tolist())
            filt_tp = st.selectbox("Tp Opção", tp_opts)
        with fcol3:
            data_opts_raw = pd.to_datetime(display_df['Dt Vencimento'], format='%d/%m/%Y').dt.date.unique().tolist()
            data_opts_raw.sort()
            data_opts_str = [d.strftime('%d/%m/%Y') for d in data_opts_raw]
            data_opts = ["Todos"] + data_opts_str
            filt_dt = st.selectbox("Vencimento", data_opts)
        with fcol4:
            status_opts = ["Todos"] + sorted(display_df['Status'].unique().tolist())
            idx_status = status_opts.index("Aberta") if "Aberta" in status_opts else 0
            filt_status = st.selectbox("Status", status_opts, index=idx_status)
            
        if filt_ativo != "Todos":
            display_df = display_df[display_df['Ativo'] == filt_ativo]
        if filt_tp != "Todos":
            display_df = display_df[display_df['Tp Opção'] == filt_tp]
        if filt_dt != "Todos":
            display_df = display_df[display_df['Dt Vencimento'] == filt_dt]
        if filt_status != "Todos":
            display_df = display_df[display_df['Status'] == filt_status]
        # ---------------
        
        display_df['diff_num'] = display_df['Diferença']
            
        display_df['Cotação Atual'] = display_df['Cotação Atual'].apply(format_brl)
        display_df['Diferença'] = display_df['Diferença'].apply(format_brl)
        display_df['Strike'] = display_df['Strike'].apply(format_brl)
        display_df['Vl Opção'] = display_df['Vl Opção'].apply(format_brl)
        display_df['Cobertura PUT'] = display_df['Cobertura PUT'].apply(format_brl)
        display_df['Vl Prêmio'] = display_df['Vl Prêmio'].apply(format_brl)
        
        def color_tp_opcao(val):
            if val == "CALL":
                return 'color: #00CC96; font-weight: bold;'
            elif val == "PUT":
                return 'color: #EF553B; font-weight: bold;'
            return ''
            
        def highlight_cols_by_rules(row):
            tp = row.get('Tp Opção', '')
            diff = row.get('diff_num', 0.0)
            
            color = ''
            if tp == 'PUT':
                if diff < 0.01:
                    color = 'color: orange;'
                elif diff > 0 and diff < 0.51:
                    color = 'color: yellow;'
            elif tp == 'CALL':
                if diff > 0:
                    color = 'color: orange;'
                elif diff > -0.51 and diff < 0:
                    color = 'color: yellow;'
                    
            cols_to_style = ['Ativo', 'Cotação Atual', 'Strike', 'Diferença']
            return [color if col in cols_to_style else '' for col in row.index]
            
        styled_df = display_df.style \
            .apply(highlight_cols_by_rules, axis=1) \
            .map(color_tp_opcao, subset=['Tp Opção']) \
            .format({'Taxa': '{:.2%}'}) \
            .set_properties(**{'text-align': 'center'}, subset=['Ativo', 'Tp Opção', 'Dt Operação', 'Dt Vencimento', 'Status']) \
            .set_properties(**{'text-align': 'right'}, subset=['Cotação Atual', 'Diferença', 'Strike', 'Quantidade', 'Vl Opção', 'Vl Prêmio', 'Cobertura PUT', 'Taxa'])
        
        selected_opcao = st.dataframe(
            styled_df, 
            use_container_width=True, 
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "id": None,
                "diff_num": None
            },
            key=f"opcoes_table_{st.session_state.refresh_id}"
        )
        
        if selected_opcao.selection.rows:
            row_idx = selected_opcao.selection.rows[0]
            selected_row = display_df.iloc[row_idx]
            
            op_raw = opcoes_df[opcoes_df['id'] == selected_row['id']].iloc[0].to_dict()
            op_raw['Cotação Atual'] = prices_dict.get(op_raw['ativo'], 0.0)
            dialog_edit_opcao(op_raw)
            
        st.markdown("---")
        if st.button("Adicionar Opção", type="primary"):
            dialog_add_opcao()
        
    st.stop()

if current_view == "Visão Geral":
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
    
    # Mapeamento de tickers para busca no Yahoo Finance (especialmente para Cripto)
    ticker_fetch_map = {}
    modified_tickers_to_fetch = []
    for t in tickers_to_fetch:
        asset_r = assets_df[assets_df['ticker'] == t].iloc[0]
        if asset_r['asset_type'] == 'Cripto' and '-' not in t:
            yf_ticker = f"{t}-USD"
            ticker_fetch_map[t] = yf_ticker
            modified_tickers_to_fetch.append(yf_ticker)
        else:
            ticker_fetch_map[t] = t
            modified_tickers_to_fetch.append(t)

    with st.spinner("Buscando preços atualizados e cotações de mercado..."):
        refresh_id = st.session_state.refresh_id
        current_prices = svc.fetch_current_prices(modified_tickers_to_fetch, refresh_id)
        
        # Prepara dados para fetch_asset_sectors (tupla para ser hashable no cache)
        assets_tuple = (tuple(assets_df['ticker'].tolist()), tuple(assets_df['asset_type'].tolist()))
        sectors_dict = svc.fetch_asset_sectors(assets_tuple, refresh_id)
        
        usd_to_brl_rate = svc.get_usd_brl_rate(refresh_id)
        btc_to_usd_rate = svc.get_btc_usd_rate(refresh_id)
        ibov_points = svc.get_ibov(refresh_id)
        
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
    
    def calculate_asset_totals(row):
        base_invested = row['quantity'] * row['average_price_brl']
        base_profit = row['current_value'] - base_invested
        
        if row['asset_type'] == 'Renda Fixa':
            return pd.Series({'profit_loss': 0.0, 'total_invested': base_invested})
            
        history_df = db.get_asset_history(row['id'], st.session_state.user_id)
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
                    2025: 1518.00
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
