import streamlit as st
import pandas as pd
import db

def render_proventos_futuros_header():
    """Renderiza o status de sincronização e o botão de consulta no topo."""
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

def render_proventos_futuros_results():
    """Renderiza a tabela de proventos provisionados quando ativado."""
    if not st.session_state.get('show_investidor10_results'):
        return

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
                    st.session_state.show_investidor10_results = False
                    st.rerun()
            with col_f2:
                total_fmt = "R$ ••••••" if is_hidden else f"R$ {total_provisionado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                st.markdown(f"<div style='text-align: right; font-size: 1.2rem; font-weight: bold; color: #00CC96; padding-top: 5px;'>Total: {total_fmt}</div>", unsafe_allow_html=True)
    st.markdown("---")
