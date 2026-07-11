# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import db
from utils.formatters import get_annual_proventos_summary, infer_asset_type
from components.ui import render_top_header

def render_proventos_resumo_view():
    render_top_header("📊 Resumo de Proventos", "Consolidado histórico de proventos recebidos por ano, moeda e classe de ativos.")
    
    proventos_df = db.get_proventos(st.session_state.user_id)
    if proventos_df.empty:
        st.info("Nenhum dado de provento registrado.")
        return

    # Usamos st.tabs para dividir as duas visões
    tab_consolidado, tab_classe = st.tabs(["📅 Evolução Anual", "📂 Distribuição por Classe"])

    def format_provento(val):
        if st.session_state.get('hide_values', False): return "••••••"
        return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not pd.isna(val) and val != 0 else "0,00"

    with tab_consolidado:
        anos_disponiveis = sorted([int(a) for a in proventos_df['ano'].unique()], reverse=True)
        
        st.markdown('<h3 style="color: #ffffff; font-size: 1.2rem; margin-bottom: 1rem;">📅 Consolidado por Ano</h3>', unsafe_allow_html=True)
        resumo_df = get_annual_proventos_summary(proventos_df, anos_disponiveis)
        
        if not resumo_df.empty:
            meses_cols = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
            display_resumo = resumo_df.copy()
            for m in meses_cols: display_resumo[m] = display_resumo[m].apply(format_provento)
            display_resumo['Valor Mensal'] = display_resumo['Valor Mensal'].apply(format_provento)
            display_resumo['Valor Anual'] = display_resumo['Valor Anual'].apply(format_provento)
            display_resumo.rename(columns={'Valor Anual': 'Valor Anual '}, inplace=True)
            
            cols_resumo = ['Ano'] + meses_cols + ['Valor Mensal', 'Valor Anual ']
            display_resumo = display_resumo[cols_resumo]
            global_max_val = resumo_df[meses_cols].values.max()

            def highlight_absolute_max(s):
                if s.name in meses_cols:
                    return ['color: #00CC96' if (resumo_df.loc[i, s.name] == global_max_val and global_max_val > 0) else '' for i in s.index]
                return ['' for _ in s]

            st.dataframe(
                display_resumo.style.apply(highlight_absolute_max, axis=0)
                              .set_properties(**{'text-align': 'center'}, subset=['Ano'])
                              .set_properties(**{'text-align': 'right'}, subset=meses_cols + ['Valor Mensal', 'Valor Anual '])
                              .set_properties(**{'color': '#00CC96'}, subset=['Valor Mensal'])
                              .set_properties(**{'color': '#3d9df3'}, subset=['Valor Anual ']),
                hide_index=True, use_container_width=True
            )

            # ---- Proventos Stocks e Reits ----
            assets_df_all = db.get_all_assets(st.session_state.user_id) 
            has_us_assets = not assets_df_all[assets_df_all['asset_type'].isin(['Stocks', 'Reits'])].empty if not assets_df_all.empty else False
            if has_us_assets:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<h3 style="color: #ffffff; font-size: 1.2rem; margin-bottom: 1rem;">💵 Proventos Dolarizados (Valores em R$)</h3>', unsafe_allow_html=True)
                with db.get_db_connection() as conn:
                    full_assets_map = {row['ticker']: row['asset_type'] for _, row in pd.read_sql_query("SELECT ticker, asset_type FROM assets", conn).iterrows()}
                us_tickers = [t for t in proventos_df['ticker'].unique() if full_assets_map.get(t, infer_asset_type(t)) in ['Stocks', 'Reits']]
                df_us_prov = proventos_df[proventos_df['ticker'].isin(us_tickers)]
                
                if not df_us_prov.empty:
                    resumo_us = df_us_prov.groupby('ano')['valor'].sum().reset_index().rename(columns={'ano': 'Ano', 'valor': 'Valor'})
                    resumo_us['Ano'] = resumo_us['Ano'].astype(str)
                    display_us = resumo_us.sort_values('Ano', ascending=True).copy()
                    display_us['Valor'] = display_us['Valor'].apply(format_provento)
                    st.dataframe(display_us.style.set_properties(**{'text-align': 'center'}, subset=['Ano']).set_properties(**{'text-align': 'right'}, subset=['Valor']), hide_index=True, use_container_width=True)
                else:
                    st.info("Nenhum provento de Stocks ou Reits registrado.")

    with tab_classe:
        # Filtros de seleção de Ano e Mês
        anos_disponiveis = sorted([int(a) for a in proventos_df['ano'].unique()], reverse=True)
        
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            ano_selecionado = st.selectbox("📅 Selecione o Ano", anos_disponiveis, key="sel_ano_classe")
        
        df_ano = proventos_df[proventos_df['ano'] == ano_selecionado]
        meses_nomes_dict = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        meses_disponiveis_nums = sorted(df_ano['mes'].unique())
        meses_opcoes = [meses_nomes_dict[m] for m in meses_disponiveis_nums]
        
        with col_sel2:
            mes_selecionado_nome = st.selectbox("🗓️ Selecione o Mês", meses_opcoes, key="sel_mes_classe")
            
        mes_selecionado_num = {v: k for k, v in meses_nomes_dict.items()}[mes_selecionado_nome]
        df_mes = df_ano[df_ano['mes'] == mes_selecionado_num].copy()
        
        # Mapeamento de tickers para tipo de ativo
        assets_df = db.get_all_assets(st.session_state.user_id)
        if not assets_df.empty:
            full_assets_map = dict(zip(assets_df['ticker'], assets_df['asset_type']))
        else:
            full_assets_map = {}
        
        df_mes['tipo_ativo'] = df_mes['ticker'].apply(lambda t: full_assets_map.get(t, infer_asset_type(t)))
        
        df_grouped = df_mes.groupby('tipo_ativo')['valor'].sum().reset_index()
        df_grouped.columns = ['Classe', 'Valor']
        df_grouped = df_grouped.sort_values(by='Valor', ascending=False)
        
        total_recebido = df_grouped['Valor'].sum()
        df_grouped['%'] = (df_grouped['Valor'] / total_recebido) * 100 if total_recebido > 0 else 0
        
        # Totalizador no topo
        st.markdown("<br>", unsafe_allow_html=True)
        total_fmt = "R$ ••••••" if st.session_state.get('hide_values', False) else f"R$ {total_recebido:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        st.markdown(
            f"""
            <div style='background-color: var(--table-header-bg); padding: 15px; border-radius: 10px; border: 1px solid var(--border-color); text-align: center; margin-bottom: 20px;'>
                <span style='font-size: 0.9rem; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;'>💰 Total Recebido no Mês</span>
                <h2 style='color: #00CC96; margin: 5px 0 0 0; font-size: 2.2rem; font-weight: bold;'>{total_fmt}</h2>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        if df_grouped.empty or total_recebido == 0:
            st.info(f"Nenhum provento recebido em {mes_selecionado_nome} de {ano_selecionado}.")
        else:
            col_tabela, col_grafico = st.columns([1, 1])
            
            with col_tabela:
                st.markdown("<h4 style='margin-bottom: 10px;'>📂 Valores por Classe</h4>", unsafe_allow_html=True)
                display_grouped = df_grouped.copy()
                display_grouped['Valor'] = display_grouped['Valor'].apply(format_provento)
                display_grouped['%'] = display_grouped['%'].apply(lambda x: f"{x:.1f}%")
                
                styled_grouped = display_grouped.style.set_properties(**{'text-align': 'center'}, subset=['%']) \
                                                     .set_properties(**{'text-align': 'right'}, subset=['Valor'])
                
                st.dataframe(styled_grouped, hide_index=True, use_container_width=True)
                
            with col_grafico:
                st.markdown("<h4 style='margin-bottom: 10px;'>📊 Distribuição Percentual</h4>", unsafe_allow_html=True)
                import plotly.express as px
                
                graph_df = df_grouped.copy()
                if st.session_state.get('hide_values', False):
                    hover_temp = "%{label}<br>%{percent}"
                    label_info = "percent+label"
                else:
                    hover_temp = "%{label}<br>R$ %{value:,.2f}<br>%{percent}"
                    label_info = "percent+label"
                    
                fig = px.pie(
                    graph_df, 
                    values='Valor', 
                    names='Classe', 
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                
                fig.update_traces(
                    textposition='inside', 
                    textinfo=label_info,
                    hovertemplate=hover_temp
                )
                
                fig.update_layout(
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                    margin=dict(t=10, b=10, l=10, r=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white')
                )
                st.plotly_chart(fig, use_container_width=True)
