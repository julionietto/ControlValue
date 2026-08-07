# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import datetime
from components.ui import create_card
import executive_report_service as exec_svc

@st.dialog("📄 Report Executivo Inteligente", width="large")
def dialog_report_executivo():
    user_id = st.session_state.get('user_id', 1)
    username = st.session_state.get('username', 'Investidor')

    with st.spinner("Analisando ativos em carteira, precificação e inteligência macroeconômica viva..."):
        try:
            pdf_bytes, perfil, objetivo, ai_narrative, underperforming = exec_svc.generate_executive_pdf_report(user_id)
            active_df, prov_df, _ = exec_svc.get_user_portfolio_data(user_id)
            active = active_df[active_df['quantity'] > 0] if not active_df.empty else active_df
            tot_invested = active['invested_brl_est'].sum() if not active.empty else 0
        except Exception as e:
            st.error(f"Erro ao gerar o Report Executivo: {e}")
            if st.button("Fechar", use_container_width=True, key="btn_err_close_modal"):
                st.rerun()
            return

    # Header / Intro Summary
    st.markdown("""
        <div style='background-color: rgba(15, 23, 42, 0.7); padding: 12px 16px; border-radius: 8px; border-left: 4px solid #1e40af; margin-bottom: 14px;'>
            <h4 style='margin: 0; color: #f8fafc;'>Inteligência Estratégica de Carteira & Panorama Macroeconômico</h4>
            <p style='margin-top: 4px; margin-bottom: 0; color: #94a3b8; font-size: 0.85rem;'>
                Análise em tempo real do perfil do investidor, objetivo patrimonial e contexto macroeconômico (Brasil & EUA).
            </p>
        </div>
    """, unsafe_allow_html=True)

    # KPI Metric Cards
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        create_card("Patrimônio Investido", f"R$ {tot_invested:,.2f}")
    with col_kpi2:
        create_card("Perfil Inferido", perfil)
    with col_kpi3:
        create_card("Objetivo Detectado", objetivo, small_font=True)
    with col_kpi4:
        count_under = len(underperforming)
        status_str = f"⚠️ {count_under} Alertas" if count_under > 0 else "✅ Carteira Equilibrada"
        create_card("Saúde do Portfólio", status_str)

    st.markdown("---")

    # Tabs
    tab_macro, tab_alerts, tab_portfolio = st.tabs([
        "🌐 Panorama Macroeconômico & Estratégia",
        "⚠️ Ativos sob Pressão / Desconto",
        "📊 Posição Atual dos Ativos"
    ])

    with tab_macro:
        st.markdown("#### 🌐 Panorama Macroeconômico Viva (IA em Tempo Real)")
        st.markdown(ai_narrative)

    with tab_alerts:
        st.markdown("#### ⚠️ Análise Setorial e Ativos com Desconto / Fatos Relevantes")
        if underperforming:
            st.warning("Os ativos abaixo apresentam cotações sob desconto ou preço médio superior ao preço teto recomendado:")
            for u in underperforming:
                with st.expander(f"📌 **{u['ticker']}** ({u['asset_type']}) — Preço Médio: R$ {u['average_price']:,.2f}"):
                    st.write(f"**Motivo / Fato Relevante:** {u['reason']}")
        else:
            st.success("🎉 Nenhum ativo da carteira apresenta desvio crítico em relação ao preço teto estipulado!")

    with tab_portfolio:
        st.markdown("#### 📊 Posição dos Ativos")
        if not active.empty:
            df_curr = active.copy()
            if 'invested_val' not in df_curr.columns:
                df_curr['invested_val'] = df_curr['quantity'] * df_curr['average_price']
            if 'weight_%' not in df_curr.columns:
                tot_inv = df_curr['invested_brl_est'].sum() if 'invested_brl_est' in df_curr.columns else df_curr['invested_val'].sum()
                df_curr['weight_%'] = (df_curr['invested_val'] / tot_inv * 100) if tot_inv > 0 else 0
            display_df = df_curr[['ticker', 'asset_type', 'quantity', 'average_price', 'currency', 'invested_val', 'weight_%']].copy()
            display_df.columns = ["Ticker", "Classe", "Quantidade", "Preço Médio", "Moeda", "Total Investido", "Peso na Carteira (%)"]
            st.dataframe(display_df, use_container_width=True)

    st.markdown("---")

    # Rodapé do Popup com 2 Botões: Fechar e Baixar Relatório
    col_close, col_download = st.columns(2)
    with col_close:
        if st.button("Fechar", use_container_width=True, key="btn_close_report_modal"):
            st.rerun()

    with col_download:
        st.download_button(
            label="📥 Baixar Relatório (PDF)",
            data=pdf_bytes,
            file_name=f"report_executivo_{username.lower()}_{datetime.date.today().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            key="btn_download_report_modal"
        )


def render_report_executivo_view():
    """Função legada de fallback se acessado diretamente."""
    dialog_report_executivo()
