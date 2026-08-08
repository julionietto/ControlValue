# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
import datetime
import pandas as pd  # type: ignore
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
from components.ui import create_card
import executive_report_service as exec_svc
import db

@st.dialog("📄 Report Executivo Inteligente & Panorama Macroeconômico", width="large")
def dialog_report_executivo():
    user_id = st.session_state.get('user_id', 1)
    username = st.session_state.get('username', 'Investidor')
    now_dt = datetime.datetime.now()
    current_year = now_dt.year
    current_month = now_dt.month

    meses_nomes_dict = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    meses_abrev_dict = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    nome_mes_atual = meses_nomes_dict.get(current_month, f"Mês {current_month}")

    with st.spinner("Analisando ativos em carteira, precificação em tempo real e inteligência macroeconômica..."):
        try:
            pdf_bytes, perfil, objetivo, ai_narrative, underperforming = exec_svc.generate_executive_pdf_report(user_id)
            assets_df, prov_df, _, total_atual, total_invested, global_proventos, total_aportes_ano = exec_svc.get_user_portfolio_data(user_id)
            active = assets_df[assets_df['quantity'] > 0] if not assets_df.empty else assets_df
            _, _, metrics, alignment = exec_svc.infer_investor_profile_and_goal(active)
        except Exception as e:
            st.error(f"Erro ao carregar o Report Executivo: {e}")
            if st.button("Fechar", use_container_width=True, key="btn_err_close_modal"):
                st.rerun()
            return

    # Header / Intro Banner
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 58, 138, 0.8) 100%); padding: 14px 18px; border-radius: 10px; border-left: 5px solid #3b82f6; margin-bottom: 16px;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <h3 style='margin: 0; color: #f8fafc; font-size: 1.25rem;'>📊 Diagnóstico Estratégico & Panorama Macroeconômico</h3>
                    <p style='margin-top: 4px; margin-bottom: 0; color: #94a3b8; font-size: 0.88rem;'>
                        Investidor: <b>{username}</b> | Perfil Detectado: <b style='color: #60a5fa;'>{perfil}</b> | Objetivo: <b style='color: #34d399;'>{objetivo}</b>
                    </p>
                </div>
                <div style='text-align: right;'>
                    <span style='background-color: #1e40af; color: #ffffff; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 0.85rem;'>
                        🎯 Aderência: {alignment}%
                    </span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 5 Cards de Métricas Principais (Item 1: Incluído Aportes Líquidos no Ano Corrente)
    col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
    with col_kpi1:
        create_card("Saldo Atual (Mercado)", f"R$ {total_atual:,.2f}")
    with col_kpi2:
        create_card("Total Investido", f"R$ {total_invested:,.2f}")
    with col_kpi3:
        create_card(f"Aportes Líquidos ({current_year})", f"R$ {total_aportes_ano:,.2f}")
    with col_kpi4:
        create_card("Proventos Totais Acumulados", f"R$ {global_proventos:,.2f}")
    with col_kpi5:
        lucro_val = total_atual - total_invested
        lucro_pct = (lucro_val / total_invested * 100) if total_invested > 0 else 0
        profit_str = f"+R$ {lucro_val:,.2f}" if lucro_val >= 0 else f"-R$ {abs(lucro_val):,.2f}"
        pct_str = f"{lucro_pct:+.2f}%"
        create_card("Resultado Patrimonial", profit_str, delta=pct_str)

    st.markdown("---")

    # Tabs Visuais
    tab_alloc, tab_prov, tab_macro = st.tabs([
        "📊 Alocação & Matriz de Aderência",
        "📈 Trajetória de Renda Passiva",
        "🌐 Panorama Macroeconômico & Alertas"
    ])

    # -----------------------------
    # TAB 1: ALOCAÇÃO & ADERÊNCIA
    # -----------------------------
    with tab_alloc:
        col_chart1, col_chart2 = st.columns([0.55, 0.45])
        with col_chart1:
            st.markdown("#### 🍩 Distribuição Atual por Classe de Ativo")
            if not active.empty:
                df_alloc = active.groupby('asset_type')['current_value'].sum().reset_index()
                df_alloc.columns = ['Classe', 'Valor']
                fig_donut = px.pie(
                    df_alloc, values='Valor', names='Classe', hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_donut.update_traces(textinfo='percent+label', hoverinfo='label+value+percent')
                fig_donut.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300, showlegend=False)
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.info("Nenhum ativo encontrado no portfólio.")

        with col_chart2:
            st.markdown("#### 🎯 Matriz de Alinhamento Estratégico")
            st.write(f"**Perfil do Investidor:** `{perfil}`")
            st.write(f"**Objetivo Patrimonial:** `{objetivo}`")
            st.progress(alignment / 100.0)
            st.caption(f"Grau de Aderência: **{alignment}%** — A composição da carteira reflete a estratégia de geração de fluxo recorrente de proventos e preservação de capital.")

            if not active.empty:
                st.markdown("**Resumo da Composição:**")
                summary_df = active.groupby('asset_type').agg(
                    total_val=('current_value', 'sum'),
                    qtd_ativos=('id', 'count')
                ).reset_index()
                summary_df['peso_%'] = summary_df['total_val'] / total_atual * 100
                summary_df.columns = ["Classe", "Total (R$)", "Nº Ativos", "Peso (%)"]
                st.dataframe(summary_df.style.format({"Total (R$)": "R$ {:,.2f}", "Peso (%)": "{:.1f}%"}), hide_index=True, use_container_width=True)

    # -----------------------------
    # TAB 2: PROVENTOS & TENDÊNCIA
    # -----------------------------
    with tab_prov:
        st.markdown("#### 📈 Evolução Histórica dos Proventos e Média Mensal Real")
        if not prov_df.empty:
            # Cálculo YTD Mês a Mês do Ano Atual (Itens 2 & 3)
            prov_raw_user = db.get_proventos(user_id)
            if not prov_raw_user.empty:
                df_curr_year = prov_raw_user[(prov_raw_user['ano'] == current_year) & (prov_raw_user['mes'] <= current_month)]
                tot_ytd = df_curr_year['valor'].sum() if not df_curr_year.empty else 0.0
            else:
                tot_ytd = 0.0

            media_ytd = tot_ytd / current_month if current_month > 0 else 0.0

            # Gráfico 1: Evolução Anual (Sincronizado com Média Mensal YTD do Ano Corrente)
            prov_df_calc = prov_df.copy()
            def calc_media_mensal_row(r):
                ano_row = int(r['ano'])
                if ano_row == current_year:
                    return media_ytd
                else:
                    meses_div = r['max_mes'] if (r['max_mes'] and r['max_mes'] > 0) else 12
                    return r['total_proventos'] / meses_div

            prov_df_calc['media_mensal'] = prov_df_calc.apply(calc_media_mensal_row, axis=1)
            prov_df_calc['total_proventos'] = prov_df_calc.apply(
                lambda r: tot_ytd if int(r['ano']) == current_year else r['total_proventos'], axis=1
            )

            fig_prov = go.Figure()
            fig_prov.add_trace(go.Bar(
                x=prov_df_calc['ano'].astype(str),
                y=prov_df_calc['total_proventos'],
                name="Total Anual (R$)",
                marker_color='#16a34a'
            ))
            fig_prov.add_trace(go.Scatter(
                x=prov_df_calc['ano'].astype(str),
                y=prov_df_calc['media_mensal'],
                name="Média Mensal Real (R$)",
                yaxis="y2",
                mode="lines+markers+text",
                text=[f"R$ {m:,.0f}" for m in prov_df_calc['media_mensal']],
                textposition="top center",
                line=dict(color='#f59e0b', width=3)
            ))
            fig_prov.update_layout(
                yaxis=dict(title="Total Anual (R$)"),
                yaxis2=dict(title="Média Mensal (R$)", overlaying="y", side="right"),
                height=300,
                margin=dict(t=20, b=20, l=20, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_prov, use_container_width=True)

            def fmt_brl_str(val):
                return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            st.info(f"💡 **Foto Atual {current_year}:** Até o mês de **{nome_mes_atual}** o valor total de proventos recebidos é de **R\\$ {fmt_brl_str(tot_ytd)}** e o valor médio recebido por mês é de **R\\$ {fmt_brl_str(media_ytd)}**.")

            st.markdown("---")
            # Item 4: Segundo gráfico Mês a Mês no ano atual (Recebidos vs Provisionados)
            st.markdown(f"#### 📅 Proventos Mês a Mês no Ano Atual ({current_year}) — Recebidos & Provisionados")

            prov_futuros_df = db.get_proventos_provisionados_calculados(user_id)
            if not prov_futuros_df.empty and 'data_pagamento' in prov_futuros_df.columns:
                prov_futuros_df['dt_pag'] = pd.to_datetime(prov_futuros_df['data_pagamento'], errors='coerce')
                prov_futuros_df['total_futuro'] = prov_futuros_df['valor'] * prov_futuros_df['quantidade_elegivel']
                df_fut_year = prov_futuros_df[prov_futuros_df['dt_pag'].dt.year == current_year]
            else:
                df_fut_year = pd.DataFrame()

            months_x = [meses_abrev_dict[m] for m in range(1, 13)]
            val_recebidos = []
            val_provisionados = []
            medias_acumuladas = []

            soma_acumulada = 0.0
            for m in range(1, 13):
                if not prov_raw_user.empty:
                    rec_val = prov_raw_user[(prov_raw_user['ano'] == current_year) & (prov_raw_user['mes'] == m)]['valor'].sum()
                else:
                    rec_val = 0.0

                if not df_fut_year.empty:
                    fut_val = df_fut_year[df_fut_year['dt_pag'].dt.month == m]['total_futuro'].sum()
                else:
                    fut_val = 0.0

                if m <= current_month:
                    r_item = float(rec_val)
                    p_item = 0.0
                else:
                    r_item = 0.0
                    p_item = max(float(rec_val), float(fut_val))

                val_recebidos.append(r_item)
                val_provisionados.append(p_item)

                soma_acumulada += (r_item + p_item)
                medias_acumuladas.append(soma_acumulada / m)

            fig_m = go.Figure()
            fig_m.add_trace(go.Bar(
                x=months_x,
                y=val_recebidos,
                name="Recebido (R$)",
                marker_color='#16a34a'
            ))
            fig_m.add_trace(go.Bar(
                x=months_x,
                y=val_provisionados,
                name="Provisionado (R$)",
                marker_color='#3b82f6'
            ))
            fig_m.add_trace(go.Scatter(
                x=months_x,
                y=medias_acumuladas,
                name="Média Acumulada (R$)",
                yaxis="y2",
                mode="lines+markers+text",
                text=[f"R$ {v:,.0f}" for v in medias_acumuladas],
                textposition="top center",
                line=dict(color='#f59e0b', width=3)
            ))
            fig_m.update_layout(
                barmode='stack',
                yaxis=dict(title="Proventos Mensais (R$)"),
                yaxis2=dict(title="Média Acumulada (R$)", overlaying="y", side="right"),
                height=320,
                margin=dict(t=20, b=20, l=20, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_m, use_container_width=True)

        else:
            st.info("Nenhum histórico de proventos cadastrado.")

    # -----------------------------
    # TAB 3: MACRO & ALERTAS (Item 5: Moedas e Preço Teto)
    # -----------------------------
    with tab_macro:
        st.markdown(ai_narrative)
        st.markdown("---")
        st.markdown("#### ⚠️ Ativos sob Pressão / Oportunidades de Reavaliação")
        if underperforming:
            st.warning("Os ativos abaixo apresentam cotações com desconto ou preço médio superior ao preço teto estipulado:")
            for u in underperforming:
                curr_sym = u.get('currency_symbol', 'R\\$')
                avg_p_str = f"{curr_sym} {u['average_price']:,.2f}"
                curr_p_str = f"{curr_sym} {u['current_price']:,.2f}"
                with st.expander(f"📌 **{u['ticker']}** ({u['asset_type']}) — Preço Médio: {avg_p_str} | Cotação: {curr_p_str}"):
                    st.write(f"**Diagnóstico:** {u['reason']}")
        else:
            st.success("🎉 Nenhum ativo da carteira apresenta desvio crítico em relação aos preços teto estipulados!")

    st.markdown("---")

    # Rodapé com 2 Botões de Ação
    col_close, col_download = st.columns(2)
    with col_close:
        if st.button("Fechar", use_container_width=True, key="btn_close_report_modal"):
            st.rerun()

    with col_download:
        st.download_button(
            label="📥 Baixar Relatório Completo (PDF)",
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

