# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import pandas as pd
import db
import services as svc
from utils.formatters import format_ticker_for_display, format_brl
from components.ui import render_top_header

def render_derivativos_view():
    render_top_header("Derivativos", "Controle de operações, travas e lançamentos cobertos.")
    
    @st.dialog("Editar Opção", width="large", dismissible=False)
    def dialog_edit_opcao(op_data):
        st.markdown("<h4 style='text-align: center; text-decoration: underline; text-underline-offset: 4px; margin-top: -20px;'>📊 Dados do Ativo</h4>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: ativo = st.text_input("Ativo", value=format_ticker_for_display(op_data['ativo']), disabled=True)
        with c2: cotacao_atual = st.number_input("Cotação Atual", value=float(op_data.get('Cotação Atual') or 0.0), disabled=True, format="%.2f")
        with c3: strike = st.number_input("Strike", min_value=0.01, step=0.01, value=float(op_data.get('strike') or 0.01), format="%.2f")
        
        st.markdown("<h4 style='text-align: center; text-decoration: underline; text-underline-offset: 4px;'>📅 Prazos e Detalhes</h4>", unsafe_allow_html=True)
        c4, c5, c6, c7, c8 = st.columns(5)
        with c4:
            try: dt_op_obj = pd.to_datetime(op_data['dt_operacao']).date()
            except: dt_op_obj = pd.Timestamp.now().date()
            dt_operacao = st.date_input("Dt Operação", value=dt_op_obj, format="DD/MM/YYYY")
        with c5:
            try: dt_venc_obj = pd.to_datetime(op_data['dt_vencimento']).date()
            except: dt_venc_obj = pd.Timestamp.now().date()
            dt_vencimento = st.date_input("Dt Vencimento", value=dt_venc_obj, format="DD/MM/YYYY")
        with c6:
            tp_opcao = st.selectbox("Tp Opção", ["CALL", "PUT"], index=0 if op_data['tp_opcao']=="CALL" else 1)
        with c7:
            derivativo = st.text_input("Derivativo", value=op_data['derivativo'])
        with c8:
            status_opts = ["Aberta", "Encerrada", "Exercida"]
            status = st.selectbox("Status", status_opts, index=status_opts.index(op_data['status']) if op_data['status'] in status_opts else 0)
            
        c_h1, c_h2, c_h3 = st.columns([1, 3, 3])
        with c_h2:
            st.markdown("<div style='text-align: center; border-bottom: 2px solid #888; margin-top: 15px; margin-bottom: 10px; font-weight: bold;'>Início da Operação</div>", unsafe_allow_html=True)
        with c_h3:
            st.markdown("<div style='text-align: center; border-bottom: 2px solid #888; margin-top: 15px; margin-bottom: 10px; font-weight: bold;'>Fim da Operação</div>", unsafe_allow_html=True)
            
        c_o1, c_o2, c_o3, c_o4, c_o5, c_o6, c_o7 = st.columns(7)
        with c_o1:
            tipo_operacao = st.selectbox("Tipo", ["VENDA", "COMPRA"], index=0 if op_data.get('tipo_operacao') != 'COMPRA' else 1)
        with c_o2:
            qtd_inicial = st.number_input("Qtd Inicial", value=int(op_data.get('qtd_inicial') or op_data.get('quantidade') or 0), step=100)
        with c_o3:
            vl_op_ini = st.number_input("Vl Opção Inicial", value=float(op_data.get('vl_opcao_inicial') or op_data.get('vl_opcao') or 0), step=0.01, format="%.2f")
        with c_o4:
            vl_premio_ini = st.number_input("Vl Prêmio Inicial", value=float(op_data.get('vl_premio_inicial') or op_data.get('vl_premio') or 0), step=0.01, format="%.2f")
        with c_o5:
            qtd_final = st.number_input("Qtd Final", value=int(op_data.get('qtd_final') or 0), step=100)
        with c_o6:
            vl_op_fin = st.number_input("Vl Opção Final", value=float(op_data.get('vl_opcao_final') or 0), step=0.01, format="%.2f")
        with c_o7:
            vl_premio_fin_calc = qtd_final * vl_op_fin
            vl_premio_fin = st.number_input("Vl Prêmio Final", value=float(vl_premio_fin_calc), step=0.01, format="%.2f")
            
        # Cálculo de Saldo e Resultado
        saldo_qtd = qtd_inicial - qtd_final
        if tipo_operacao == "VENDA":
            res_val = vl_premio_ini - vl_premio_fin
        else:
            res_val = vl_premio_fin - vl_premio_ini
            
        st.markdown(f"""
        <div style='background-color: rgba(0, 204, 150, 0.1); padding: 15px; border-radius: 10px; border: 1px solid #00CC96; text-align: center;'>
            <span style='font-size: 1.05rem; font-weight: bold;'>Resultado da Operação:</span>
            <span style='font-size: 1rem; margin-left: 10px;'>Quantidade em Aberto: <b>{int(saldo_qtd)}</b></span>
            <span style='font-size: 1rem; margin: 0 15px;'>|</span>
            <span style='font-size: 1rem;'>Valor em Aberto: <b style='color: {"#00CC96" if res_val >= 0 else "#EF553B"};'>{format_brl(res_val)}</b></span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            if st.button("Salvar Alterações", type="primary", use_container_width=True):
                dt_op_str = dt_operacao.strftime("%Y-%m-%d")
                dt_venc_str = dt_vencimento.strftime("%Y-%m-%d")
                db.update_opcao(
                    op_data['id'], st.session_state.user_id, op_data['ativo'], strike, tp_opcao, dt_op_str, dt_venc_str, derivativo, 
                    saldo_qtd, vl_op_ini, vl_premio_ini, status,
                    tipo_operacao, qtd_inicial, vl_op_ini, vl_premio_ini,
                    qtd_final, vl_op_fin, vl_premio_fin, res_val
                )
                st.session_state.refresh_id += 1
                st.success("Operação atualizada!")
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
        st.markdown("""
        <h3 style='text-align: center; margin-top: -20px; margin-bottom: 5px;'>🆕 Adicionar Nova Operação de Derivativo</h3>
        <h4 style='text-align: center; text-decoration: underline; text-underline-offset: 4px; margin-top: 0;'>📊 Dados do Ativo</h4>
        """, unsafe_allow_html=True)
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
            
        st.markdown("<h4 style='text-align: center; text-decoration: underline; text-underline-offset: 4px;'>📅 Prazos e Detalhes</h4>", unsafe_allow_html=True)
        c4, c5, c6, c7 = st.columns(4)
        with c4:
            dt_operacao = st.date_input("Dt Operação", value=pd.Timestamp.now().date(), format="DD/MM/YYYY")
        with c5:
            dt_vencimento = st.date_input("Dt Vencimento", value=pd.Timestamp.now().date(), format="DD/MM/YYYY")
        with c6:
            tp_opcao = st.selectbox("Tp Opção", ["CALL", "PUT"])
        with c7:
            derivativo = st.text_input("Derivativo")
            
        c_h1, c_h2 = st.columns([1, 3])
        with c_h2:
            st.markdown("<div style='text-align: center; border-bottom: 2px solid #888; margin-top: 15px; margin-bottom: 10px; font-weight: bold;'>Início da Operação</div>", unsafe_allow_html=True)
            
        c_i1, c_i2, c_i3, c_i4 = st.columns(4)
        with c_i1:
            tipo_op = st.selectbox("Tipo", ["VENDA", "COMPRA"])
        with c_i2:
            qtd_ini = st.number_input("Qtd Inicial", value=100, step=100)
        with c_i3:
            vl_op_ini = st.number_input("Vl Opção Inicial", min_value=0.00, step=0.01, format="%.2f")
        with c_i4:
            vl_prem_ini_calc = vl_op_ini * qtd_ini
            vl_prem_ini = st.number_input("Vl Prêmio Inicial", value=float(vl_prem_ini_calc), step=0.01, format="%.2f")

        status = "Aberta"
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("Salvar Operação", type="primary", use_container_width=True):
                if ativo_val:
                    dt_op_str = dt_operacao.strftime("%Y-%m-%d")
                    dt_venc_str = dt_vencimento.strftime("%Y-%m-%d")
                    db.insert_opcao(
                        ativo_val, strike, tp_opcao, dt_op_str, dt_venc_str, derivativo, 
                        qtd_ini, vl_op_ini, vl_prem_ini, status, st.session_state.user_id,
                        tipo_op, qtd_ini, vl_op_ini, vl_prem_ini, 0, 0, 0, vl_prem_ini if tipo_op == "VENDA" else -vl_prem_ini
                    )
                    st.session_state.refresh_id += 1
                    st.success("Operação adicionada!")
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
        st.info("Nenhum derivativo registrado para essa conta.")
        if st.button("Adicionar Opção", type="primary"):
            dialog_add_opcao()
    else:
        display_df = opcoes_df.copy()
        
        tickers = display_df['ativo'].unique().tolist()
        prices_dict = svc.fetch_current_prices(tickers, st.session_state.refresh_id)
        
        # Garantia contra cotação zerada: tentar repescagem para ativos com cotação zerada
        zero_tickers = [t for t in tickers if prices_dict.get(t, 0.0) <= 0.0]
        if zero_tickers:
            fresh_prices = svc.fetch_current_prices(zero_tickers, st.session_state.refresh_id + 999)
            for zt, zp in fresh_prices.items():
                if zp > 0.0:
                    prices_dict[zt] = zp

        display_df['Cotação Atual'] = display_df['ativo'].map(prices_dict).fillna(0.0)
        
        display_df['Diferença'] = display_df['Cotação Atual'] - display_df['strike']
        display_df['Taxa'] = display_df['vl_opcao'] / display_df['strike']
        display_df['Cobertura PUT'] = display_df.apply(
            lambda row: row['quantidade'] * row['strike'] if row['tp_opcao'] == 'PUT' else None, axis=1
        )
        display_df['Oper'] = display_df['tipo_operacao'].apply(lambda x: 'Compra' if x == 'COMPRA' else 'Venda')
        
        # Lógica para tratar campos legados vs novos
        display_df['Vl Operação'] = display_df['resultado'].fillna(display_df['vl_premio'])
        display_df['Saldo Qtd'] = display_df['quantidade']
        
        display_df = display_df.sort_values(['dt_vencimento', 'ativo'])
        
        display_df['dt_operacao_fmt'] = pd.to_datetime(display_df['dt_operacao']).dt.strftime('%d/%m/%Y')
        display_df['dt_vencimento_fmt'] = pd.to_datetime(display_df['dt_vencimento']).dt.strftime('%d/%m/%Y')
        
        display_df['ativo_display'] = display_df['ativo'].apply(format_ticker_for_display)
        
        # Renomear colunas para o display seguindo a nova lógica
        display_df.rename(columns={
            'ativo_display': 'Ativo',
            'strike': 'Strike',
            'tp_opcao': 'Tp Opção',
            'dt_operacao_fmt': 'Dt Operação',
            'dt_vencimento_fmt': 'Dt Vencimento',
            'derivativo': 'Derivativo',
            'vl_opcao': 'Vl Opção',
            'status': 'Status'
        }, inplace=True)
        
        ordem_colunas = [
            'id', 'Ativo', 'Cotação Atual', 'Strike', 'Diferença', 'Tp Opção', 
            'Dt Operação', 'Dt Vencimento', 'Derivativo', 'Saldo Qtd', 
            'Vl Opção', 'Vl Operação', 'Oper', 'Taxa', 'Cobertura PUT', 'Status'
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
        
        total_vl_operacao = display_df['Vl Operação'].sum()
        
        display_df['diff_num'] = display_df['Diferença']
        
        is_hidden = st.session_state.get('hide_values', False)
        def safe_format_brl(val):
            if pd.isna(val) or val is None or val == "":
                return ""
            return "R$ ••••••" if is_hidden else format_brl(val)
            
        display_df['Cotação Atual'] = display_df['Cotação Atual'].apply(safe_format_brl)
        display_df['Diferença'] = display_df['Diferença'].apply(safe_format_brl)
        display_df['Strike'] = display_df['Strike'].apply(safe_format_brl)
        display_df['Vl Opção'] = display_df['Vl Opção'].apply(safe_format_brl)
        display_df['Cobertura PUT'] = display_df['Cobertura PUT'].apply(safe_format_brl)
        display_df['Vl Operação'] = display_df['Vl Operação'].apply(safe_format_brl)
        
        if is_hidden:
            display_df['Saldo Qtd'] = "••••••"
            display_df['Taxa'] = "••••••"
        
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
            .map(color_tp_opcao, subset=['Tp Opção'])
            
        if not is_hidden:
            styled_df = styled_df.format({'Taxa': '{:.2%}'})
            
        styled_df = styled_df.set_properties(**{'text-align': 'center'})
        
        col_config = {
            "id": None,
            "diff_num": None
        }
        for col in [c for c in ordem_colunas if c not in ['id', 'diff_num']]:
            try:
                col_config[col] = st.column_config.Column(alignment="center")
            except (TypeError, AttributeError, Exception):
                try:
                    col_config[col] = st.column_config.TextColumn(alignment="center")
                except (TypeError, AttributeError, Exception):
                    col_config[col] = st.column_config.Column()

        selected_opcao = st.dataframe(
            styled_df, 
            use_container_width=True, 
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config=col_config,
            key=f"opcoes_table_{st.session_state.refresh_id}"
        )
        
        total_fmt = "R$ ••••••" if is_hidden else format_brl(total_vl_operacao)
        st.markdown(f"<div style='text-align: right; font-size: 1.25rem; font-weight: bold;'>Total Vl Operação: <span style='color: {"#00CC96" if total_vl_operacao >= 0 else "#EF553B"};'>{total_fmt}</span></div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        if selected_opcao.selection.rows:
            row_idx = selected_opcao.selection.rows[0]
            selected_row = display_df.iloc[row_idx]
            
            op_raw = opcoes_df[opcoes_df['id'] == selected_row['id']].iloc[0].to_dict()
            op_raw = {k: (v if pd.notna(v) else None) for k, v in op_raw.items()}
            op_raw['Cotação Atual'] = prices_dict.get(op_raw['ativo'], 0.0)
            dialog_edit_opcao(op_raw)
            
        st.markdown("---")
        if st.button("Adicionar Opção", type="primary"):
            dialog_add_opcao()
        
    st.stop()
