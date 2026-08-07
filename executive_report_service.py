# pyrefly: ignore[missing-import]
import os
import datetime
import io
import psycopg2
import psycopg2.extras
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from dotenv import load_dotenv

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

import db
import services as svc

load_dotenv(r"c:\Projeto\ControlValue\.env")

# Try initializing Gemini API
try:
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        GEMINI_AVAILABLE = True
    else:
        GEMINI_AVAILABLE = False
except Exception:
    GEMINI_AVAILABLE = False


def get_user_portfolio_data(user_id):
    """
    Calcula de forma precisa e idêntica à Visão Geral do aplicativo:
    - Saldo Atual da Carteira (Valor de Mercado) em BRL
    - Total Investido em BRL
    - Total de Proventos Globais Acumulados
    - Histórico Anual de Proventos e Média Mensal Real YTD
    """
    assets_df = db.get_all_assets(user_id)
    if assets_df.empty:
        return pd.DataFrame(), pd.DataFrame(), f"Investidor #{user_id}", 0.0, 0.0, 0.0

    all_histories_df = db.get_all_asset_histories(user_id)
    MANUAL_TYPES = ['Renda Fixa', 'Fundo CETIP']
    tickers_to_fetch = assets_df[~assets_df['asset_type'].isin(MANUAL_TYPES)]['ticker'].unique().tolist()

    ticker_fetch_map = {}
    tickers_br, tickers_us, tickers_crypto = [], [], []

    for t in tickers_to_fetch:
        asset_r = assets_df[assets_df['ticker'] == t].iloc[0]
        a_type = asset_r['asset_type']
        if a_type == 'Cripto':
            yf_t = f"{t}-USD" if '-' not in t else t
            ticker_fetch_map[t] = yf_t
            tickers_crypto.append(yf_t)
        elif a_type in ['Stocks', 'Reits']:
            ticker_fetch_map[t] = t
            tickers_us.append(t)
        else:
            ticker_fetch_map[t] = t
            tickers_br.append(t)

    all_tickers = tickers_br + tickers_us + tickers_crypto
    try:
        current_prices = svc.fetch_current_prices(all_tickers, 1)
        usd_to_brl_rate = svc.get_usd_brl_rate(1, True)
    except Exception:
        current_prices = {}
        usd_to_brl_rate = 5.5

    def get_current_price(row):
        if row['asset_type'] in MANUAL_TYPES:
            return row['average_price']
        ticker = row['ticker']
        yf_ticker = ticker_fetch_map.get(ticker, ticker)
        return current_prices.get(yf_ticker, row['average_price'])

    def apply_exchange_rate(row, column_name, is_market_price=False):
        val = row[column_name]
        if row['currency'] == 'USD' or (is_market_price and row['asset_type'] in ['Cripto', 'Stocks', 'Reits']):
            return val * usd_to_brl_rate
        return val

    assets_df['original_current_price'] = assets_df.apply(get_current_price, axis=1)
    assets_df['average_price_brl'] = assets_df.apply(lambda row: apply_exchange_rate(row, 'average_price', is_market_price=False), axis=1)
    assets_df['current_price'] = assets_df.apply(lambda row: apply_exchange_rate(row, 'original_current_price', is_market_price=True), axis=1)

    assets_df['total_invested'] = assets_df['quantity'] * assets_df['average_price_brl']
    assets_df['current_value'] = assets_df['quantity'] * assets_df['current_price']

    def calculate_asset_totals(row):
        base_invested = row['quantity'] * row['average_price_brl']
        base_profit = row['current_value'] - base_invested
        
        if row['asset_type'] in MANUAL_TYPES:
            if abs(row['quantity']) < 1e-5:
                return pd.Series({'profit_loss': 0.0, 'total_invested': 0.0})
            return pd.Series({'profit_loss': 0.0, 'total_invested': base_invested})
            
        if not all_histories_df.empty:
            history_df = all_histories_df[all_histories_df['asset_id'] == row['id']].copy()
        else:
            history_df = pd.DataFrame()
        
        if history_df.empty:
            if abs(row['quantity']) < 1e-5:
                return pd.Series({'profit_loss': 0.0, 'total_invested': 0.0})
            return pd.Series({'profit_loss': base_profit, 'total_invested': base_invested})
            
        def convert_to_brl(val):
            if row['currency'] == 'USD':
                return val * usd_to_brl_rate
            return val

        history_df['unit_price_brl'] = history_df['unit_price'].apply(convert_to_brl)
        history_df['valor_operacao'] = history_df['quantity'] * history_df['unit_price_brl']
        history_df['valor_atualizado'] = history_df['quantity'] * row['current_price']
        history_df['lucro_prejuizo'] = history_df['valor_atualizado'] - history_df['valor_operacao']
        
        if abs(row['quantity']) < 1e-5:
            return pd.Series({'profit_loss': history_df['lucro_prejuizo'].sum(), 'total_invested': 0.0})
        
        return pd.Series({'profit_loss': history_df['lucro_prejuizo'].sum(), 'total_invested': history_df['valor_operacao'].sum()})

    totals_df = assets_df.apply(calculate_asset_totals, axis=1)
    assets_df['profit_loss'] = totals_df['profit_loss']
    assets_df['invested_brl_est'] = totals_df['total_invested']

    tot_brl = assets_df['current_value'].sum()
    assets_df['weight_%'] = (assets_df['current_value'] / tot_brl * 100) if tot_brl > 0 else 0

    # Proventos
    prov_raw = db.get_proventos(user_id)
    if not prov_raw.empty:
        prov_df = prov_raw.groupby('ano').agg(
            total_proventos=('valor', 'sum'),
            max_mes=('mes', 'max')
        ).reset_index().sort_values('ano', ascending=True)
    else:
        prov_df = pd.DataFrame(columns=['ano', 'total_proventos', 'max_mes'])

    global_proventos = db.get_all_total_proventos(user_id)
    u_details = db.get_user_details(user_id)
    username = u_details['username'] if u_details else f"Investidor #{user_id}"

    current_total_value = assets_df[assets_df['quantity'] > 0]['current_value'].sum()
    total_invested = assets_df[assets_df['quantity'] > 0]['invested_brl_est'].sum()

    return assets_df, prov_df, username, current_total_value, total_invested, global_proventos


def infer_investor_profile_and_goal(active_df):
    """
    Infere o perfil de risco (Conservador, Moderado, Arrojado) e o objetivo principal
    (Renda Passiva, Valorização / Crescimento, Misto) com base na composição da carteira.
    """
    if active_df.empty:
        return "Conservador", "Renda Passiva", {}, 50
        
    tot_val = active_df['current_value'].sum()
    if tot_val == 0:
        return "Conservador", "Renda Passiva", {}, 50
        
    weights = active_df.groupby('asset_type')['current_value'].sum() / tot_val * 100
    w_fiis = weights.get('Fiis', 0)
    w_acoes = weights.get('Ações', 0) + weights.get('Aes', 0)
    w_rf = weights.get('Renda Fixa', 0)
    w_reits = weights.get('Reits', 0)
    w_stocks = weights.get('Stocks', 0)
    w_cripto_etf = weights.get('Cripto', 0) + weights.get('ETF', 0)
    
    # Perfil
    if (w_rf + w_fiis) >= 65 and w_cripto_etf < 5:
        perfil = "Conservador"
    elif w_cripto_etf > 15 or w_reits + w_stocks > 35 or w_acoes > 50:
        perfil = "Arrojado"
    else:
        perfil = "Moderado"
        
    # Objetivo
    yield_focused = w_fiis + w_reits + (w_acoes * 0.6) + (w_rf * 0.5)
    growth_focused = w_cripto_etf + w_stocks + (w_acoes * 0.4)
    
    if yield_focused >= 55:
        objetivo = "Foco em Crescimento de Renda Passiva"
        alignment_score = min(98, int(yield_focused * 1.15))
    elif growth_focused >= 40:
        objetivo = "Foco em Crescimento e Valorização Patrimonial"
        alignment_score = min(95, int(growth_focused * 1.25))
    else:
        objetivo = "Perfil Misto (Renda Passiva & Valorização)"
        alignment_score = 85
        
    metrics = {
        "w_fiis": w_fiis, "w_acoes": w_acoes, "w_rf": w_rf,
        "w_reits": w_reits, "w_stocks": w_stocks, "w_cripto_etf": w_cripto_etf,
        "tot_val": tot_val
    }
    return perfil, objetivo, metrics, alignment_score


def analyze_asset_performance(active_df):
    """
    Avalia a saúde dos ativos (Lucro/Prejuízo, Desconto vs Preço Teto).
    """
    underperforming = []
    if active_df.empty:
        return underperforming
        
    for _, row in active_df.iterrows():
        ticker = row['ticker']
        a_type = row['asset_type']
        avg_price = row['average_price']
        curr_price = row.get('current_price', avg_price)
        teto = row.get('ceiling_price', 0)
        
        profit_loss = row.get('profit_loss', 0)
        
        if profit_loss < -500 or (teto and teto > 0 and curr_price < teto * 0.9):
            reason = f"Ativo sob pressão no mercado. Cotação atual de R$ {curr_price:,.2f} versus Preço Médio R$ {avg_price:,.2f} (Preço Teto Estipulado: R$ {teto:,.2f}). Oportunidade de aporte ou reavaliação setorial."
            underperforming.append({
                "ticker": ticker,
                "asset_type": a_type,
                "average_price": avg_price,
                "current_price": curr_price,
                "reason": reason
            })
    return underperforming


def generate_ai_macro_narrative(username, perfil, objetivo, active_df, prov_df):
    """Gera briefing macroeconômico usando a API Gemini ou fallback dinâmico robusto."""
    current_year = datetime.date.today().year

    if GEMINI_AVAILABLE:
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = f"""
            Você é um estrategista sênior de investimentos especialista nos mercados do Brasil e EUA.
            Elabore um resumo executivo compacto e dinâmico (máximo 4 parágrafos pequenos) para o investidor {username}.
            
            Perfil: {perfil} | Objetivo: {objetivo}
            
            Contexto Macroeconômico Atual:
            - Brasil: Taxa Selic, Inflação IPCA e atratividade da Renda Fixa IPCA+ e FIIs.
            - EUA: Taxa do Federal Reserve, câmbio USD/BRL e desempenho de Stocks/Reits.
            - Estratégia: Como a carteira focada em renda passiva deve se posicionar para maximizar dividendos e proteger capital.
            
            Responda em formato Markdown profissional e direto.
            """
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception:
            pass

    # Fallback Narrativa de Alta Qualidade
    return f"""
#### 🌐 Panorama Macroeconômico & Estratégia de Renda Passiva ({current_year})

**Brasil & Taxa de Juros:**
O cenário nacional permanece marcado por taxas de juros (Selic) em patamares atrativos, sustentando retornos expressivos em títulos de Renda Fixa atrelados ao **IPCA+** e **CDI**. Para ativos de Renda Variável focados em dividendos — em especial **Fundos Imobiliários (FIIs)** e **Ações de Setores Perenes** (Bancos, Energia, Saneamento) —, o momento oferece excelentes taxas de retorno sobre o custo (*Yield on Cost*).

**Mercado Internacional & Câmbio (EUA):**
A alocação em ativos norte-americanos (**Stocks** e **REITs**) oferece uma dupla proteção: diversificação geográfica de receitas e proteção cambial em **Dólar (USD)**. Com a política monetária dos EUA caminhando para estabilização, ativos globais pagadores de proventos continuam a gerar fluxo de caixa sólido e dolarizado.

**Diagnóstico & Recomendações:**
A carteira do investidor **{username}** está aderente ao perfil **{perfil}** e ao objetivo **{objetivo}**. A estratégia de aportes direcionados para Renda Fixa IPCA+ e ativos imobiliários/ações de dividendos nos EUA fortalece o crescimento composto da renda passiva a longo prazo.
"""


def generate_executive_pdf_report(user_id):
    """Gera o arquivo PDF executivo usando ReportLab e Matplotlib."""
    assets_df, prov_df, username, total_atual, total_invested, global_proventos = get_user_portfolio_data(user_id)
    active = assets_df[assets_df['quantity'] > 0] if not assets_df.empty else pd.DataFrame()
    perfil, objetivo, metrics, alignment = infer_investor_profile_and_goal(active)
    underperforming = analyze_asset_performance(active)
    ai_narrative = generate_ai_macro_narrative(username, perfil, objetivo, active, prov_df)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1e3a8a'),
        fontName='Helvetica-Bold',
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#475569'),
        fontName='Helvetica',
        spaceAfter=14
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1e40af'),
        fontName='Helvetica-Bold',
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )

    story = []

    # Title Banner
    story.append(Paragraph(f"REPORT EXECUTIVO — CONTROLVALUE", title_style))
    story.append(Paragraph(f"Investidor: <b>{username}</b> | Data de Emissão: {datetime.date.today().strftime('%d/%m/%Y')} | Perfil: <b>{perfil}</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1e40af'), spaceAfter=12))

    # KPI Table Card
    kpi_data = [
        [
            Paragraph("<b>Saldo Atual (Mercado)</b>", body_style),
            Paragraph("<b>Total Investido</b>", body_style),
            Paragraph("<b>Proventos Totais</b>", body_style),
            Paragraph("<b>Aderência Estratégica</b>", body_style)
        ],
        [
            Paragraph(f"<font size=11 color='#1e3a8a'><b>R$ {total_atual:,.2f}</b></font>", body_style),
            Paragraph(f"<font size=11 color='#334155'><b>R$ {total_invested:,.2f}</b></font>", body_style),
            Paragraph(f"<font size=11 color='#16a34a'><b>R$ {global_proventos:,.2f}</b></font>", body_style),
            Paragraph(f"<font size=11 color='#2563eb'><b>{alignment}% Alinhado</b></font>", body_style)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[130, 130, 130, 130])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # Matplotlib Allocation Donut Chart Buffer
    if not active.empty:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3.2))
        
        # Donut Allocation
        alloc = active.groupby('asset_type')['current_value'].sum()
        colors_list = ['#2563eb', '#16a34a', '#d97706', '#9333ea', '#dc2626', '#0891b2']
        ax1.pie(alloc.values, labels=alloc.index, autopct='%1.1f%%', colors=colors_list[:len(alloc)], startangle=140, wedgeprops=dict(width=0.4, edgecolor='w'))
        ax1.set_title("Alocação por Classe de Ativo", fontsize=10, fontweight='bold', color='#1e3a8a')

        # Passive Income Bar Chart
        if not prov_df.empty:
            ax2.bar(prov_df['ano'].astype(str), prov_df['total_proventos'], color='#16a34a', alpha=0.85)
            ax2.set_title("Evolução dos Proventos por Ano (R$)", fontsize=10, fontweight='bold', color='#16a34a')
            ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'R${x/1000:.0f}k' if x>=1000 else f'R${x:.0f}'))
            ax2.tick_params(axis='x', rotation=30, labelsize=8)
            ax2.grid(axis='y', linestyle='--', alpha=0.5)
        else:
            ax2.text(0.5, 0.5, 'Sem dados de proventos', horizontalalignment='center', verticalalignment='center')

        plt.tight_layout()
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=150)
        plt.close(fig)
        img_buf.seek(0)

        story.append(Image(img_buf, width=7*inch, height=2.8*inch))
        story.append(Spacer(1, 10))

    # Section 1: Executive Macro Narrative
    story.append(Paragraph("1. Panorama Macroeconômico & Inteligência de Mercado", section_heading))
    for para in ai_narrative.split('\n\n'):
        clean_p = para.replace('#', '').strip()
        if clean_p:
            story.append(Paragraph(clean_p, body_style))
    story.append(Spacer(1, 10))

    # Section 2: Underperforming / Opportunity Assets
    if underperforming:
        story.append(Paragraph("2. Ativos sob Pressão / Oportunidades de Reavaliação", section_heading))
        for u in underperforming:
            story.append(Paragraph(f"• <b>{u['ticker']}</b> ({u['asset_type']}) — Preço Médio: R$ {u['average_price']:,.2f} | Cotação: R$ {u['current_price']:,.2f}", body_style))
            story.append(Paragraph(f"  <i>Diagnóstico: {u['reason']}</i>", body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue(), perfil, objetivo, ai_narrative, underperforming
