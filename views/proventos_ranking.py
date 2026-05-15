# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import db
import plotly.express as px  # type: ignore # pyrefly: ignore[missing-import]
from utils.formatters import format_ticker_for_display
from components.ui import render_top_header

def render_proventos_ranking_view():
    render_top_header("🏆 Ranking de Pagadores", "Visualização dos ativos que mais geraram renda passiva na sua carteira.")
    
    proventos_df = db.get_proventos(st.session_state.user_id)
    if proventos_df.empty:
        st.info("Nenhum dado de provento registrado.")
        return

    anos_disponiveis = sorted([int(a) for a in proventos_df['ano'].unique()], reverse=True)
    st.markdown("<br>", unsafe_allow_html=True)
    ano_selecionado = st.selectbox("Selecione o Ano para o Ranking", anos_disponiveis, key="ano_ranking_prov")
    
    df_ano_ranking = proventos_df[proventos_df['ano'] == ano_selecionado].copy()
    
    if not df_ano_ranking.empty:
        ranking_df = df_ano_ranking.groupby('ticker')['valor'].sum().reset_index()
        ranking_df.rename(columns={'valor': 'Valor Anual', 'ticker': 'Ativo'}, inplace=True)
        ranking_df['Ativo'] = ranking_df['Ativo'].apply(format_ticker_for_display)
        ranking_df = ranking_df.sort_values(by='Valor Anual', ascending=False).reset_index(drop=True)
        ranking_df.index = ranking_df.index + 1
        ranking_df = ranking_df.reset_index().rename(columns={'index': 'Posição'})
        
        max_val = ranking_df['Valor Anual'].max()
        if not st.session_state.get('hide_values', False):
            fig = px.bar(ranking_df, x='Ativo', y='Valor Anual', text_auto='.2f', color='Valor Anual', color_continuous_scale='tempo', template='plotly_dark')
            fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False, marker_line_color="#1f1f1f", marker_line_width=1, opacity=0.9)
            fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False, xaxis=dict(title=""), yaxis=dict(title="Valor Anual (R$)", range=[0, max_val * 1.15], showgrid=True, gridcolor="#333333"), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Gráfico oculto para privacidade.")
        
        is_hidden = st.session_state.get('hide_values', False)
        ranking_display = ranking_df.copy()
        ranking_display['Posição'] = ranking_display['Posição'].apply(lambda x: f"#{x}")
        ranking_display['Valor Anual'] = ranking_display['Valor Anual'].apply(lambda val: "R$ ••••••" if is_hidden else f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        st.dataframe(ranking_display.style.set_properties(**{'text-align': 'center'}, subset=['Posição', 'Ativo']).set_properties(**{'text-align': 'right'}, subset=['Valor Anual']), hide_index=True, use_container_width=True)
    else:
        st.info(f"Nenhum provento registrado para o ano {ano_selecionado}.")
    
    st.stop()
