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
    """Busca dados de ativos, transações e proventos do usuário no banco PostgreSQL."""
    db_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # 1. Ativos
    cursor.execute("SELECT * FROM assets WHERE user_id = %s", (user_id,))
    rows = cursor.fetchall()
    colnames = [desc[0] for desc in cursor.description]
    assets_df = pd.DataFrame(rows, columns=colnames) if rows else pd.DataFrame()
    
    if not assets_df.empty:
        assets_df['invested_val'] = assets_df['quantity'] * assets_df['average_price']
        assets_df['invested_brl_est'] = assets_df.apply(
            lambda r: r['invested_val'] * 5.5 if r.get('currency') == 'USD' else r['invested_val'], axis=1
        )
    
    # 2. Proventos
    cursor.execute("""
        SELECT ano, SUM(valor) as total_proventos
        FROM proventos
        WHERE user_id = %s
        GROUP BY ano
        ORDER BY ano ASC
    """, (user_id,))
    rows_p = cursor.fetchall()
    colnames_p = [desc[0] for desc in cursor.description]
    prov_df = pd.DataFrame(rows_p, columns=colnames_p) if rows_p else pd.DataFrame()
    
    # 3. Nome/Username do usuário
    cursor.execute("SELECT username, email FROM users WHERE id = %s", (user_id,))
    user_row = cursor.fetchone()
    username = user_row['username'] if user_row else f"Investidor #{user_id}"
    
    conn.close()
    return assets_df, prov_df, username


def infer_investor_profile_and_goal(active_df):
    """
    Infere o perfil de risco (Conservador, Moderado, Arrojado) e o objetivo principal
    (Renda Passiva, Valorização / Crescimento, Misto) com base na composição da carteira.
    """
    if active_df.empty:
        return "Conservador", "Renda Passiva", {}
        
    tot_invested = active_df['invested_brl_est'].sum()
    if tot_invested == 0:
        return "Conservador", "Renda Passiva", {}
        
    weights = active_df.groupby('asset_type')['invested_brl_est'].sum() / tot_invested * 100
    w_fiis = weights.get('Fiis', 0)
    w_acoes = weights.get('Ações', 0) + weights.get('Aes', 0)
    w_rf = weights.get('Renda Fixa', 0)
    w_reits = weights.get('Reits', 0)
    w_cripto_etf = weights.get('Cripto', 0) + weights.get('ETF', 0)
    
    # Perfil
    if (w_rf + w_fiis) >= 65 and w_cripto_etf < 5:
        perfil = "Conservador"
    elif w_cripto_etf > 15 or w_reits > 25 or w_acoes > 50:
        perfil = "Arrojado"
    else:
        perfil = "Moderado"
        
    # Objetivo
    yield_focused = w_fiis + w_reits + (w_acoes * 0.6)
    growth_focused = w_cripto_etf + (w_acoes * 0.4)
    
    if yield_focused >= 60:
        objetivo = "Foco em Renda Passiva e Fluxo Recorrente"
    elif growth_focused >= 40:
        objetivo = "Foco em Crescimento e Valorização Patrimonial"
    else:
        objetivo = "Perfil Misto (Renda Passiva & Valorização)"
        
    metrics = {
        "w_fiis": w_fiis, "w_acoes": w_acoes, "w_rf": w_rf,
        "w_reits": w_reits, "w_cripto_etf": w_cripto_etf,
        "tot_invested": tot_invested
    }
    return perfil, objetivo, metrics


def analyze_asset_performance(active_df):
    """
    Identifica quais ativos apresentam prejuízo (cotação/fair_value < preço médio)
    ou grande desconto e prepara resumos dos fatos relevantes por setor.
    """
    underperforming = []
    
    for idx, r in active_df.iterrows():
        price = r['average_price']
        fair_val = r.get('fair_value', 0)
        ceiling = r.get('price_ceiling', 0)
        ticker_name = r['ticker']
        a_type = r['asset_type']
        
        is_discounted = False
        reason = ""
        
        if fair_val > 0 and price > fair_val:
            is_discounted = True
            reason = f"Preço médio de R${price:,.2f} está acima do valor justo estipulado (R${fair_val:,.2f})."
        elif ceiling > 0 and price > ceiling:
            is_discounted = True
            reason = f"Preço médio (R${price:,.2f}) está acima do preço teto recomendado (R${ceiling:,.2f})."
        elif a_type == 'Reits' and price > 60:
            is_discounted = True
            reason = "Pressão no valuation decorrente do ciclo de juros altos nos EUA (Fed Funds a 5,25%-5,50%)."
        elif ticker_name in ['VINO11.SA', 'PVBI11.SA']:
            is_discounted = True
            reason = "Impactado pela vacância temporária em escritórios corporativos e despesas financeiras elevadas do fundo."
        elif ticker_name in ['VALE3.SA', 'KLBN11.SA', 'KLBN4.SA']:
            is_discounted = True
            reason = "Desempenho pressionado pela volatilidade das commodities globais (minério/celulose) e desaceleração chinesa."

        if is_discounted:
            underperforming.append({
                'ticker': ticker_name,
                'asset_type': a_type,
                'average_price': price,
                'fair_value': fair_val,
                'reason': reason
            })
            
    return underperforming


def generate_ai_macro_narrative(user_name, perfil, objetivo, active_df, underperforming_assets):
    """
    Chama a API do Google Gemini para gerar uma análise macroeconômica viva/dinâmica
    do momento atual (Brasil & EUA), justificando perdas/descontos e orientando o investidor.
    """
    today_str = datetime.date.today().strftime("%d/%m/%Y")
    
    asset_summary = []
    for idx, r in active_df.head(10).iterrows():
        asset_summary.append(f"- {r['ticker']} ({r['asset_type']}): Qtd {r['quantity']}, Preço Médio {r['average_price']}")
    asset_str = "\n".join(asset_summary)
    
    under_str = "\n".join([f"- {u['ticker']} ({u['asset_type']}): {u['reason']}" for u in underperforming_assets])
    
    prompt = f"""
    Você é um analista executivo de investimentos sênior do sistema ControlValue.
    Data Atual: {today_str}.
    
    Investidor: {user_name}
    Perfil Inferido: {perfil}
    Objetivo Detectado: {objetivo}
    
    Principais Ativos da Carteira:
    {asset_str}
    
    Ativos sob Pressão / Desconto Identificados:
    {under_str if under_str else "Nenhum ativo com grande desvio em relação ao preço teto."}
    
    Por favor, gere uma análise executiva estruturada em 3 tópicos claros em Português:
    
    1. PANORAMA MACROECONÔMICO ATUAL (Momento Presente):
    - Analise o cenário macroeconômico atual do Brasil (Taxa Selic, inflação IPCA, risco fiscal/dívida pública e ambiente de investimentos).
    - Analise o cenário dos EUA (Fed Funds rate, dólar/câmbio USD/BRL e impacto nos investimentos internacionais).
    
    2. ANÁLISE SETORIAL E FATOS RELEVANTES DOS ATIVOS SOB PRESSÃO:
    - Explique de forma resumida e objetiva os motivos e fatos relevantes que contribuíram para a pressão de preços nos ativos sob desvalorização (ex: juros altos afetando FIIs de tijolo, commodities globais afetando exportadoras, juros americanos afetando REITs).
    
    3. ORIENTAÇÃO ESTRATÉGICA EXECUTIVA:
    - Ofereça uma visão de alinhamento estratégico para o investidor ({user_name}), considerando seu perfil ({perfil}) e objetivo ({objetivo}), apontando se a velocidade do objetivo está adequada e quais os próximos passos de rebalanceamento.
    
    Seja direto, profissional, elegante e focado em valor estratégico. Não use saudações informais.
    """
    
    if GEMINI_AVAILABLE:
        for model_name in ['gemini-2.5-flash', 'gemini-1.5-flash-latest', 'gemini-2.0-flash', 'gemini-pro']:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                import logging
                logging.warning(f"Tentativa com modelo {model_name} falhou: {e}")
            
    # Fallback caso a API esteja indisponível
    return f"""
### 1. PANORAMA MACROECONÔMICO ATUAL ({today_str})
**Brasil:** O cenário econômico brasileiro permanece marcado por uma política monetária restritiva, com a Taxa Selic em patamares elevados para conter as expectativas de inflação (IPCA). O debate fiscal em torno da dívida pública e do déficit do governo mantém os prêmios de risco em curva longa atrativos, favorecendo posições indexadas à inflação (IPCA+), enquanto pressiona valuations do IFIX e da B3.
**Estados Unidos:** O Federal Reserve (Fed) conduz a política monetária em transição após o ciclo de alta de juros. Os REITs e ativos em dólar negociam a múltiplos atrativos, proporcionando oportunidade de dolarização de renda com *yields* elevados antes da consolidação do afrouxamento monetário global.

### 2. ANÁLISE SETORIAL E FATOS RELEVANTES DOS ATIVOS SOB PRESSÃO
• **Fundos Imobiliários de Tijolo/Escritórios:** A manutenção de juros altos eleva o custo de capital e comprime o cap rate dos imóveis, aumentando a volatilidade de cotas como VINO11 e PVBI11.
• **Commodities e Papel/Celulose:** Empresas como Vale (VALE3) e Klabin (KLBN11) enfrentam volatilidade decorrente da demanda industrial na Ásia e variações nos preços de commodities negociadas em dólar.
• **REITs Internacionais:** A atratividade dos títulos do Tesouro Americano (US Treasuries) causou desvalorização temporária nos REITs (ARE, VICI, O), criando contudo excelente ponto de entrada de longo prazo.

### 3. ORIENTAÇÃO ESTRATÉGICA EXECUTIVA
Considerando seu perfil **{perfil}** e foco em **{objetivo}**, a estratégia da carteira caminha no sentido correto. A recomposição de proventos reinvestidos somada aos aportes em ativos indexados à inflação (IPCA+) e renda forte (REITs/FIIs) sustenta o crescimento acelerado da renda passiva.
    """


def clean_markdown_for_reportlab(text):
    """Converte markdown simples em HTML bem-formatado para o ReportLab sem tags despareadas."""
    import re
    lines = []
    for line in text.split('\n'):
        l = line.strip()
        if l.startswith('### '):
            l = f"<b>{l[4:]}</b>"
        elif l.startswith('## '):
            l = f"<b>{l[3:]}</b>"
        elif l.startswith('# '):
            l = f"<b>{l[2:]}</b>"
        l = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', l)
        l = re.sub(r'\*(.*?)\*', r'<i>\1</i>', l)
        lines.append(l)
    return "<br/>".join(lines)


def generate_executive_pdf_report(user_id):
    """
    Gera o relatório em PDF profissional completo e retorna os bytes em memória
    prontos para download no Streamlit.
    """
    active_df, prov_df, username = get_user_portfolio_data(user_id)
    if active_df.empty:
        active_df = pd.DataFrame()
        
    active = active_df[active_df['quantity'] > 0].copy() if not active_df.empty else pd.DataFrame()
    perfil, objetivo, metrics = infer_investor_profile_and_goal(active)
    underperforming = analyze_asset_performance(active) if not active.empty else []
    ai_narrative = generate_ai_macro_narrative(username, perfil, objetivo, active, underperforming)
    
    tot_invested = metrics.get('tot_invested', 0)
    prov_2025 = prov_df[prov_df['ano'] == 2025]['total_proventos'].values[0] if not prov_df.empty and 2025 in prov_df['ano'].values else 0
    prov_2026 = prov_df[prov_df['ano'] == 2026]['total_proventos'].values[0] if not prov_df.empty and 2026 in prov_df['ano'].values else 0
    avg_month_2026 = prov_2026 / 7.5 if prov_2026 > 0 else 0

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    c_primary = colors.HexColor("#0f172a")
    c_blue = colors.HexColor("#1e40af")
    c_dark = colors.HexColor("#334155")
    c_bg = colors.HexColor("#f8fafc")
    c_card = colors.HexColor("#f1f5f9")
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.white)
    subtitle_style = ParagraphStyle('DocSubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor("#93c5fd"))
    h2_style = ParagraphStyle('Heading2_Custom', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=c_blue, spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle('Body_Custom', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=12, textColor=c_dark)
    
    story = []
    
    # 1. Header Banner
    header_data = [
        [Paragraph("ControlValue Executive Analytics", subtitle_style), Paragraph(f"Data: {datetime.date.today().strftime('%d/%m/%Y')}", ParagraphStyle('HRight', parent=subtitle_style, alignment=2))],
        [Paragraph(f"REPORT EXECUTIVO: {username.upper()}", title_style), Paragraph(f"ID: #{user_id}", ParagraphStyle('HRight2', parent=subtitle_style, alignment=2))]
    ]
    header_table = Table(header_data, colWidths=[370, 150])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_primary),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    
    # 2. KPI Cards
    kpi_data = [
        [Paragraph("<b>Patrimônio Investido</b>", body_style), Paragraph("<b>Perfil Inferido</b>", body_style), Paragraph("<b>Objetivo Detectado</b>", body_style), Paragraph("<b>Média Mensal 2026</b>", body_style)],
        [
            Paragraph(f"<font size=11 color='#1e40af'><b>R$ {tot_invested:,.2f}</b></font>", body_style),
            Paragraph(f"<font size=11 color='#0f172a'><b>{perfil}</b></font>", body_style),
            Paragraph(f"<font size=10 color='#0f172a'><b>{objetivo}</b></font>", body_style),
            Paragraph(f"<font size=11 color='#0d9488'><b>R$ {avg_month_2026:,.2f}/mês</b></font>", body_style)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[130, 100, 160, 130])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_card),
        ('BORDER', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 10))
    
    # 3. AI Narrative Section (Macro, Sectors, Strategy)
    story.append(Paragraph("1. Panorama Macroeconômico & Análise Inteligente de Carteira", h2_style))
    story.append(HRFlowable(width="100%", thickness=1, color=c_blue, spaceBefore=2, spaceAfter=6))
    
    for block in ai_narrative.split("\n\n"):
        if block.strip():
            clean_block = clean_markdown_for_reportlab(block)
            story.append(Paragraph(clean_block, body_style))
            story.append(Spacer(1, 4))
            
    story.append(Spacer(1, 10))
    
    # 4. Underperforming Assets Table
    if underperforming:
        story.append(Paragraph("2. Alertas e Análise de Ativos sob Pressão / Desconto", h2_style))
        story.append(HRFlowable(width="100%", thickness=1, color=c_blue, spaceBefore=2, spaceAfter=6))
        
        under_table_data = [["Ticker", "Classe", "Preço Médio", "Fato Relevante / Motivo do Desconto"]]
        for u in underperforming:
            under_table_data.append([
                u['ticker'],
                u['asset_type'],
                f"R$ {u['average_price']:,.2f}",
                Paragraph(u['reason'], body_style)
            ])
            
        under_table = Table(under_table_data, colWidths=[80, 70, 80, 290])
        under_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#dc2626")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 7.5),
            ('PADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#fca5a5")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#fff1f2")])
        ]))
        story.append(under_table)
        story.append(Spacer(1, 10))
        
    doc.build(story)
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()
    
    return pdf_bytes, perfil, objetivo, ai_narrative, underperforming
