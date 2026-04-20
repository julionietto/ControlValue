import streamlit as st
import pandas as pd
import database as db
import services as svc
from utils.formatters import format_ticker_for_display, format_brl
from components.ui import render_top_header

def render_derivativos_view():
    render_top_header("Derivativos", "Controle de opções, travas e lançamentos cobertos.")
    
    @st.dialog("Editar Opção", width="large", dismissible=False)
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

    @st.dialog("Confirmar Exclusão de Opção", dismissible=False)
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

    @st.dialog("Adicionar Opção", width="large", dismissible=False)
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
        
        total_vl_premio = display_df['Vl Prêmio'].sum()
        
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
        
        st.markdown(f"<div style='text-align: right; font-size: 1.25rem; font-weight: bold;'>Total Vl Prêmio: <span style='color: #00CC96;'>{format_brl(total_vl_premio)}</span></div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
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
