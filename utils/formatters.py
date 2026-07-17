import html
import pandas as pd

def format_ticker_for_display(ticker_str):
    if isinstance(ticker_str, str) and ticker_str.endswith(".SA"):
        return ticker_str[:-3]
    return ticker_str

def escape_html(text):
    """Sanitiza strings de entrada convertendo caracteres perigosos (XSS) em HTML entities."""
    if text is None: return ""
    return html.escape(str(text))

def format_brl(value):
    """Formata um float para o padrão de moeda brasileiro (R$ X.XXX,XX)"""
    try:
        # Formata com 2 casas decimais, usando vírgula no final e ponto como separador de milhar
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return value

def infer_asset_type(ticker):
    ticker = ticker.upper()
    from db.assets import CRYPTO_ETFS
    if ticker in CRYPTO_ETFS:
        return 'ETF'
    if ticker.endswith('.SA'):
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            sector = info.get('sector', '')
            industry = info.get('industry', '')
            long_name_raw = info.get('longName')
            long_name = str(long_name_raw).upper() if long_name_raw else ""
            
            if sector == 'Real Estate' and 'REIT' in str(industry):
                return 'Fiis'
                
            # Fallback inteligente pelo nome (muitos FIIs/Fiagros não têm setor definido no Yahoo)
            fii_keywords = [' FII', 'FII ', 'FUNDO DE INVESTIMENTO IMOBILI', 'FUNDO INVESTIMENTO IMOBILI', 'CREDITO IMOBILIARIO', 'FIAGRO', 'FUNDO DE INVEST IMOB', 'IMOBIL']
            if any(k in long_name for k in fii_keywords):
                return 'Fiis'
                
            etf_keywords = ['ETF', 'FUNDO DE INDICE', 'INDEX FUND', 'ISHARES']
            if any(k in long_name for k in etf_keywords):
                return 'ETF'
                
            if not sector and not industry:
                if not long_name:
                    if '11.SA' in ticker or ticker.endswith('11'):
                        return 'Fiis'
                    return 'Ações'
                return 'ETF'
                
            return 'Ações'
        except Exception:
            if '11.SA' in ticker:
                return 'Fiis'
            return 'Ações'
    elif '-' in ticker or ticker in ['BTC', 'ETH', 'SOL', 'USDT', 'USDC']:
        return 'Cripto'
    else:
        return 'Reits'

def get_annual_proventos_summary(proventos_df, anos_disponiveis):
    import datetime
    current_date = datetime.date.today()
    current_year = current_date.year
    current_month = current_date.month

    meses_ordem = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    meses_abrev = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr',
        5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago',
        9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    }

    resumo_rows = []
    for ano in anos_disponiveis:
        df_ano = proventos_df[proventos_df['ano'] == ano]
        pivot_ano = df_ano.pivot_table(index='ticker', columns='mes', values='valor', aggfunc='sum').fillna(0)

        for mes in meses_ordem:
            if mes not in pivot_ano.columns:
                pivot_ano[mes] = 0.0

        totais_mes = pivot_ano[meses_ordem].sum(axis=0)
        retorno_total = totais_mes.sum()
        
        if int(ano) == current_year:
            soma_ate_atual = sum(totais_mes[m] for m in range(1, current_month + 1))
            media_mensal = soma_ate_atual / current_month
        else:
            media_mensal = retorno_total / 12

        row = {'Ano': str(ano), 'Ano_Int': int(ano)}
        for mes_num, abrev in meses_abrev.items():
            row[abrev] = totais_mes[mes_num]
        row['Valor Mensal'] = media_mensal
        row['Valor Anual'] = retorno_total
        resumo_rows.append(row)

    resumo_df = pd.DataFrame(resumo_rows)
    if not resumo_df.empty:
        resumo_df = resumo_df.sort_values('Ano_Int', ascending=True).drop(columns=['Ano_Int'])
    return resumo_df

def parse_currency(val):
    if pd.isna(val) or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    if not val_str:
        return 0.0
    # Remover símbolos de moeda e espaços
    val_clean = val_str.replace('R$', '').replace('$', '').replace(' ', '')
    # Se contiver pontos e vírgulas, ex: 1.250,50 -> 1250.50
    if '.' in val_clean and ',' in val_clean:
        val_clean = val_clean.replace('.', '').replace(',', '.')
    # Se contiver apenas vírgula como separador decimal (formato BR), ex: 38,50 -> 38.50
    elif ',' in val_clean:
        val_clean = val_clean.replace(',', '.')
    try:
        return float(val_clean)
    except ValueError:
        return 0.0
