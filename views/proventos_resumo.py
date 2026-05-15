# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import db
from utils.formatters import get_annual_proventos_summary, infer_asset_type
from components.ui import render_top_header

def render_proventos_resumo_view():
    render_top_header("📊 Resumo Anual", "Consolidado histórico de proventos recebidos por ano e moeda.")
    
    proventos_df = db.get_proventos(st.session_state.user_id)
    if proventos_df.empty:
        st.info("Nenhum dado de provento registrado.")
        return

    anos_disponiveis = sorted([int(a) for a in proventos_df['ano'].unique()], reverse=True)
    
    def format_provento(val):
        if st.session_state.get('hide_values', False): return "••••••"
        return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not pd.isna(val) and val != 0 else "0,00"

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
        has_us_assets = not assets_df_all[assets_df_all['asset_type'].isin(['Stocks', 'Reits'])].empty
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
