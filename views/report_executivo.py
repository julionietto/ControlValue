# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import datetime
from components.ui import render_top_header, create_card
import executive_report_service as exec_svc

def render_report_executivo_view():
    render_top_header(
        title="📄 Report Executivo",
        subtitle="Análise Macroeconômica Viva, Diagnóstico de Perfil & Relatório para Download"
    )

    user_id = st.session_state.get('user_id', 1)
    username = st.session_state.get('username', 'Investidor')

    st.markdown("""
        <div style='background-color: rgba(15, 23, 42, 0.6); padding: 16px; border-radius: 8px; border-left: 4px solid #1e40af; margin-bottom: 20px;'>
            <h4 style='margin: 0; color: #f8fafc;'>📊 Inteligência Executiva de Investimentos em Tempo Real</h4>
            <p style='margin-top: 6px; margin-bottom: 0; color: #94a3b8; font-size: 0.9rem;'>
                Esta ferramenta analisa a composição viva da sua carteira, infere seu perfil de risco e objetivo patrimonial, 
                e cruza com o panorama macroeconômico atual (Brasil & EUA) via IA para gerar pareceres setoriais e justificativas de ativos sob desvalorização.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # State key for cached report in session
    if 'report_data' not in st.session_state or st.session_state.get('report_user_id') != user_id:
        st.session_state.report_data = None
        st.session_state.report_user_id = user_id

    col_btn1, col_btn2 = st.columns([0.4, 0.6], vertical_alignment="center")
    with col_btn1:
        generate_clicked = st.button("🚀 Emitir Report Executivo Atualizado", type="primary", use_container_width=True)
        
    if generate_clicked or st.session_state.report_data is None:
        with st.spinner("Analisando ativos em carteira, precificação e processando inteligência macroeconômica..."):
            try:
                pdf_bytes, perfil, objetivo, ai_narrative, underperforming = exec_svc.generate_executive_pdf_report(user_id)
                active_df, prov_df, _ = exec_svc.get_user_portfolio_data(user_id)
                active = active_df[active_df['quantity'] > 0] if not active_df.empty else active_df
                tot_invested = active['invested_brl_est'].sum() if not active.empty else 0
                
                st.session_state.report_data = {
                    'pdf_bytes': pdf_bytes,
                    'perfil': perfil,
                    'objetivo': objetivo,
                    'ai_narrative': ai_narrative,
                    'underperforming': underperforming,
                    'tot_invested': tot_invested,
                    'active_df': active,
                    'generated_at': datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                }
            except Exception as e:
                st.error(f"Erro ao processar o Report Executivo: {e}")
                return

    rep = st.session_state.report_data
    if rep:
        with col_btn2:
            st.download_button(
                label="📥 Baixar Report Executivo em PDF",
                data=rep['pdf_bytes'],
                file_name=f"report_executivo_{username.lower()}_{datetime.date.today().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        st.caption(f"⏱️ Relatório gerado em: **{rep['generated_at']}**")

        # KPI Cards Top Section
        col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
        with col_kpi1:
            create_card("Patrimônio Investido", f"R$ {rep['tot_invested']:,.2f}")
        with col_kpi2:
            create_card("Perfil de Risco Inferido", rep['perfil'])
        with col_kpi3:
            create_card("Objetivo Detectado", rep['objetivo'], small_font=True)
        with col_kpi4:
            count_under = len(rep['underperforming'])
            status_str = f"⚠️ {count_under} Alertas" if count_under > 0 else "✅ Carteira Equilibrada"
            create_card("Saúde do Portfólio", status_str)

        st.markdown("---")

        # Tabs layout
        tab_macro, tab_alerts, tab_portfolio = st.tabs([
            "🌐 Panorama Macroeconômico & Estratégia",
            "⚠️ Análise Setorial & Ativos sob Desconto",
            "📊 Detalhamento dos Ativos em Carteira"
        ])

        with tab_macro:
            st.markdown("### 🌐 Panorama Macroeconômico e Diagnóstico Inteligente")
            st.markdown(rep['ai_narrative'])

        with tab_alerts:
            st.markdown("### ⚠️ Ativos sob Pressão / Desconto em Relação ao Preço Teto / Justo")
            if rep['underperforming']:
                st.warning("Os ativos abaixo foram identificados com preços médios superiores aos preços teto estipulados ou sob pressão setorial temporária:")
                for u in rep['underperforming']:
                    with st.expander(f"📌 **{u['ticker']}** ({u['asset_type']}) — Preço Médio: R$ {u['average_price']:,.2f}"):
                        st.write(f"**Diagnóstico / Fato Relevante:** {u['reason']}")
            else:
                st.success("🎉 Nenhum ativo em carteira apresenta desvio crítico ou prejuízo relevante frente aos preços teto cadastrados!")

        with tab_portfolio:
            st.markdown("### 📊 Posição Atual dos Ativos")
            if not rep['active_df'].empty:
                display_df = rep['active_df'][['ticker', 'asset_type', 'quantity', 'average_price', 'currency', 'invested_val', 'weight_%']].copy()
                display_df.columns = ["Ticker", "Classe", "Quantidade", "Preço Médio", "Moeda", "Total Investido", "Peso na Carteira (%)"]
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info("Nenhum ativo com quantidade maior que zero encontrado.")
