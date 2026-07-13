# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import db
from utils.formatters import get_annual_proventos_summary, infer_asset_type
from components.ui import render_top_header

@st.cache_data(ttl=10)
def get_cached_proventos(user_id):
    return db.get_proventos(user_id)

@st.cache_data(ttl=10)
def get_cached_assets(user_id):
    return db.get_all_assets(user_id)

def format_provento(val):
    if st.session_state.get('hide_values', False): return "••••••"
    return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not pd.isna(val) and val != 0 else "0,00"

@st.dialog("🔍 Detalhamento por Ativo", width="medium")
def show_proventos_classe_dialog(classe, df_ano, df_mes, full_assets_map):
    st.markdown(f"### Classe: **{classe}**")
    st.write("Detalhamento dos proventos recebidos por ativo nesta classe.")
    
    # Filtrar e agrupar mês
    df_mes_classe = df_mes[df_mes['tipo_ativo'] == classe].copy() if not df_mes.empty else pd.DataFrame()
    if not df_mes_classe.empty:
        df_mes_grouped = df_mes_classe.groupby('ticker')['valor'].sum().reset_index()
        df_mes_grouped.columns = ['Ativo', 'Valor Mês']
    else:
        df_mes_grouped = pd.DataFrame(columns=['Ativo', 'Valor Mês'])
        
    # Filtrar e agrupar ano
    df_ano_classe = df_ano[df_ano['tipo_ativo'] == classe].copy() if not df_ano.empty else pd.DataFrame()
    if not df_ano_classe.empty:
        df_ano_grouped = df_ano_classe.groupby('ticker')['valor'].sum().reset_index()
        df_ano_grouped.columns = ['Ativo', 'Valor Ano']
    else:
        df_ano_grouped = pd.DataFrame(columns=['Ativo', 'Valor Ano'])
        
    # Merge
    df_merged_assets = pd.merge(df_ano_grouped, df_mes_grouped, on='Ativo', how='outer').fillna(0)
    df_merged_assets = df_merged_assets.sort_values('Valor Ano', ascending=False)
    df_merged_assets = df_merged_assets[['Ativo', 'Valor Mês', 'Valor Ano']]
    
    # Formatação
    display_assets = df_merged_assets.copy()
    display_assets['Valor Mês'] = display_assets['Valor Mês'].apply(format_provento)
    display_assets['Valor Ano'] = display_assets['Valor Ano'].apply(format_provento)
    
    styled_assets = display_assets.style.set_properties(**{'text-align': 'right'}, subset=['Valor Mês', 'Valor Ano']) \
                                         .set_properties(**{'color': '#00CC96'}, subset=['Valor Mês']) \
                                         .set_properties(**{'color': '#3d9df3'}, subset=['Valor Ano'])
    
    st.dataframe(styled_assets, hide_index=True, use_container_width=True)

def render_proventos_resumo_view():
    render_top_header("📊 Resumo de Proventos", "Consolidado histórico de proventos recebidos por ano, moeda e classe de ativos.")
    
    proventos_df = get_cached_proventos(st.session_state.user_id)
    if proventos_df.empty:
        st.info("Nenhum dado de provento registrado.")
        return

    # Otimização: Carrega os ativos apenas uma vez usando cache
    assets_df = get_cached_assets(st.session_state.user_id)
    if not assets_df.empty:
        full_assets_map = dict(zip(assets_df['ticker'], assets_df['asset_type']))
    else:
        full_assets_map = {}

    # Usamos st.tabs para dividir as duas visões
    tab_consolidado, tab_classe = st.tabs(["📅 Evolução Anual", "📂 Distribuição por Classe"])


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
            has_us_assets = not assets_df[assets_df['asset_type'].isin(['Stocks', 'Reits'])].empty if not assets_df.empty else False
            if has_us_assets:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<h3 style="color: #ffffff; font-size: 1.2rem; margin-bottom: 1rem;">💵 Proventos Dolarizados (Valores em R$)</h3>', unsafe_allow_html=True)
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
        
        # Determina o ano atual por padrão
        from datetime import datetime
        ano_atual = datetime.now().year
        default_ano_idx = anos_disponiveis.index(ano_atual) if ano_atual in anos_disponiveis else 0
        
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            ano_selecionado = st.selectbox("📅 Selecione o Ano", anos_disponiveis, index=default_ano_idx, key="sel_ano_classe")
        
        df_ano = proventos_df[proventos_df['ano'] == ano_selecionado]
        meses_nomes_dict = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        meses_disponiveis_nums = sorted(df_ano['mes'].unique())
        meses_opcoes = [meses_nomes_dict[m] for m in meses_disponiveis_nums]
        
        # Determina o mês atual por padrão
        mes_atual_num = datetime.now().month
        mes_atual_nome = meses_nomes_dict.get(mes_atual_num, "")
        default_mes_idx = meses_opcoes.index(mes_atual_nome) if mes_atual_nome in meses_opcoes else 0
        
        with col_sel2:
            mes_selecionado_nome = st.selectbox("🗓️ Selecione o Mês", meses_opcoes, index=default_mes_idx, key="sel_mes_classe")
            
        mes_selecionado_num = {v: k for k, v in meses_nomes_dict.items()}[mes_selecionado_nome]
        
        # Otimizado: full_assets_map já foi carregado e mapeado no início da view
        
        df_ano_filtered = df_ano.copy()
        df_ano_filtered['tipo_ativo'] = df_ano_filtered['ticker'].apply(lambda t: full_assets_map.get(t, infer_asset_type(t)))
        
        df_grouped_ano = df_ano_filtered.groupby('tipo_ativo')['valor'].sum().reset_index()
        df_grouped_ano.columns = ['Classe', 'Valor Ano']
        df_grouped_ano = df_grouped_ano.sort_values(by='Valor Ano', ascending=False)
        total_recebido_ano = df_grouped_ano['Valor Ano'].sum()
        df_grouped_ano['% Ano'] = (df_grouped_ano['Valor Ano'] / total_recebido_ano) * 100 if total_recebido_ano > 0 else 0
        
        if df_grouped_ano.empty or total_recebido_ano == 0:
            st.info(f"Nenhum provento recebido em {ano_selecionado}.")
        else:
            df_mes = df_ano[df_ano['mes'] == mes_selecionado_num].copy()
            df_mes['tipo_ativo'] = df_mes['ticker'].apply(lambda t: full_assets_map.get(t, infer_asset_type(t)))
            df_grouped_mes = df_mes.groupby('tipo_ativo')['valor'].sum().reset_index()
            df_grouped_mes.columns = ['Classe', 'Valor Mês']
            df_grouped_mes = df_grouped_mes.sort_values(by='Valor Mês', ascending=False)
            total_recebido_mes = df_grouped_mes['Valor Mês'].sum()
            df_grouped_mes['% Mês'] = (df_grouped_mes['Valor Mês'] / total_recebido_mes) * 100 if total_recebido_mes > 0 else 0
            
            # Merge
            df_merged = pd.merge(df_grouped_ano[['Classe', 'Valor Ano', '% Ano']], df_grouped_mes[['Classe', 'Valor Mês', '% Mês']], on='Classe', how='outer').fillna(0)
            df_merged = df_merged.sort_values(by='Valor Ano', ascending=False)
            df_merged = df_merged[['Classe', 'Valor Mês', '% Mês', 'Valor Ano', '% Ano']]
            
            # Totalizadores no topo
            st.markdown("<br>", unsafe_allow_html=True)
            col_tot1, col_tot2 = st.columns(2)
            
            total_fmt = "R$ ••••••" if st.session_state.get('hide_values', False) else f"R$ {total_recebido_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            total_ano_fmt = "R$ ••••••" if st.session_state.get('hide_values', False) else f"R$ {total_recebido_ano:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            with col_tot1:
                st.markdown(
                    f"""
                    <div style='background-color: var(--table-header-bg); padding: 15px; border-radius: 10px; border: 1px solid var(--border-color); text-align: center; margin-bottom: 20px;'>
                        <span style='font-size: 0.9rem; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;'>💰 Total Recebido no Mês</span>
                        <h2 style='color: #00CC96; margin: 5px 0 0 0; font-size: 2.2rem; font-weight: bold;'>{total_fmt}</h2>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
            with col_tot2:
                st.markdown(
                    f"""
                    <div style='background-color: var(--table-header-bg); padding: 15px; border-radius: 10px; border: 1px solid var(--border-color); text-align: center; margin-bottom: 20px;'>
                        <span style='font-size: 0.9rem; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;'>📅 Total Recebido no Ano</span>
                        <h2 style='color: #3d9df3; margin: 5px 0 0 0; font-size: 2.2rem; font-weight: bold;'>{total_ano_fmt}</h2>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            
            col_tabela, col_grafico_mes, col_grafico_ano = st.columns([1.2, 1, 1])
            
            with col_tabela:
                st.markdown("<h4 style='margin-bottom: 10px;'>📂 Valores por Classe</h4>", unsafe_allow_html=True)
                display_grouped = df_merged.copy()
                display_grouped['Valor Mês'] = display_grouped['Valor Mês'].apply(format_provento)
                display_grouped['% Mês'] = display_grouped['% Mês'].apply(lambda x: f"{x:.1f}%" if x > 0 else "0,0%")
                display_grouped['Valor Ano'] = display_grouped['Valor Ano'].apply(format_provento)
                display_grouped['% Ano'] = display_grouped['% Ano'].apply(lambda x: f"{x:.1f}%" if x > 0 else "0,0%")
                
                styled_grouped = display_grouped.style.set_properties(**{'text-align': 'center'}, subset=['% Mês', '% Ano']) \
                                                     .set_properties(**{'text-align': 'right'}, subset=['Valor Mês', 'Valor Ano']) \
                                                     .set_properties(**{'color': '#00CC96'}, subset=['Valor Mês']) \
                                                     .set_properties(**{'color': '#3d9df3'}, subset=['Valor Ano'])
                
                selected_row = st.dataframe(
                    styled_grouped, 
                    hide_index=True, 
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key=f"proventos_classe_table_{st.session_state.refresh_id}"
                )
                
                if selected_row.selection.rows:
                    row_idx = selected_row.selection.rows[0]
                    classe_selecionada = df_merged.iloc[row_idx]['Classe']
                    show_proventos_classe_dialog(classe_selecionada, df_ano_filtered, df_mes, full_assets_map)
                
            import plotly.express as px
            classes_unicas = df_merged['Classe'].unique()
            palette = px.colors.qualitative.Pastel
            color_map = {cls: palette[i % len(palette)] for i, cls in enumerate(classes_unicas)}
            
            with col_grafico_mes:
                st.markdown("<h4 style='margin-bottom: 10px;'>📊 Distribuição do Mês</h4>", unsafe_allow_html=True)
                if total_recebido_mes == 0:
                    st.info(f"Nenhum provento no mês.")
                else:
                    graph_df_mes = df_merged[df_merged['Valor Mês'] > 0].copy()
                    if st.session_state.get('hide_values', False):
                        hover_temp = "%{label}<br>%{percent}"
                        label_info = "percent+label"
                    else:
                        hover_temp = "%{label}<br>R$ %{value:,.2f}<br>%{percent}"
                        label_info = "percent+label"
                        
                    fig_mes = px.pie(
                        graph_df_mes, 
                        values='Valor Mês', 
                        names='Classe', 
                        hole=0.4,
                        color='Classe',
                        color_discrete_map=color_map
                    )
                    
                    fig_mes.update_traces(
                        textposition='inside', 
                        textinfo=label_info,
                        hovertemplate=hover_temp
                    )
                    
                    fig_mes.update_layout(
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                        margin=dict(t=10, b=10, l=10, r=10),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white')
                    )
                    st.plotly_chart(fig_mes, use_container_width=True)
                    
            with col_grafico_ano:
                st.markdown("<h4 style='margin-bottom: 10px;'>📊 Acumulado do Ano</h4>", unsafe_allow_html=True)
                graph_df_ano = df_merged[df_merged['Valor Ano'] > 0].copy()
                
                if st.session_state.get('hide_values', False):
                    hover_temp = "%{label}<br>%{percent}"
                    label_info = "percent+label"
                else:
                    hover_temp = "%{label}<br>R$ %{value:,.2f}<br>%{percent}"
                    label_info = "percent+label"
                    
                fig_ano = px.pie(
                    graph_df_ano, 
                    values='Valor Ano', 
                    names='Classe', 
                    hole=0.4,
                    color='Classe',
                    color_discrete_map=color_map
                )
                
                fig_ano.update_traces(
                    textposition='inside', 
                    textinfo=label_info,
                    hovertemplate=hover_temp
                )
                
                fig_ano.update_layout(
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                    margin=dict(t=10, b=10, l=10, r=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white')
                )
                st.plotly_chart(fig_ano, use_container_width=True)
