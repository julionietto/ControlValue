import yfinance as yf
import pandas as pd
import streamlit as st

@st.cache_data(ttl=300)
def fetch_current_prices(tickers, refresh_id=0):
    """
    Busca os preços atuais para uma lista de tickers usando yfinance.
    Retorna um dicionário mapeando o ticker para seu preço atual.
    """
    if not tickers:
        return {}
    
    prices = {}
    for ticker in tickers:
        try:
            ticker_obj = yf.Ticker(ticker)
            # Tenta pegar o preço mais recente
            data = ticker_obj.history(period="1d")
            if not data.empty:
                current_price = data['Close'].iloc[-1]
                prices[ticker] = float(current_price)
            else:
                # Fallback para info fast se o history falhar
                try:
                    current_price = ticker_obj.fast_info['lastPrice']
                    prices[ticker] = float(current_price)
                except Exception:
                    prices[ticker] = 0.0
                    print(f"Não foi possível obter preço para {ticker}")
        except Exception as e:
            print(f"Erro ao buscar o preço de {ticker}: {e}")
            prices[ticker] = 0.0 # Define 0 se houver erro
            
    return prices

@st.cache_data(ttl=300)
def get_usd_brl_rate(refresh_id=0):
    """
    Busca a cotação atual do Dólar em Reais usando o ticker BRL=X.
    """
    try:
        data = yf.Ticker("BRL=X").history(period="1d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
        else:
            return float(yf.Ticker("BRL=X").fast_info['lastPrice'])
    except Exception as e:
        print(f"Erro ao buscar cotação USD/BRL: {e}")
        return 5.0 # Valor de fallback razoável em caso de erro da API

@st.cache_data(ttl=300)
def get_btc_usd_rate(refresh_id=0):
    """
    Busca a cotação atual do Bitcoin em Dólar usando o ticker BTC-USD.
    """
    try:
        data = yf.Ticker("BTC-USD").history(period="1d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
        else:
            return float(yf.Ticker("BTC-USD").fast_info['lastPrice'])
    except Exception as e:
        print(f"Erro ao buscar cotação BTC/USD: {e}")
        return 0.0

@st.cache_data(ttl=300)
def get_ibov(refresh_id=0):
    """
    Busca a pontuação atual do IBOVESPA usando o ticker ^BVSP.
    """
    try:
        data = yf.Ticker("^BVSP").history(period="1d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
        else:
            return float(yf.Ticker("^BVSP").fast_info['lastPrice'])
    except Exception as e:
        print(f"Erro ao buscar pontuação do IBOV: {e}")
        return 0.0

SECTOR_TRANSLATION = {
    "Basic Materials": "Materiais Básicos",
    "Communication Services": "Serviços de Comunicação",
    "Consumer Cyclical": "Consumo Cíclico",
    "Consumer Defensive": "Consumo Defensivo",
    "Energy": "Óleo e Gás",  # Padrão solicitado para Energy global
    "Financial Services": "Serviços Financeiros",
    "Healthcare": "Saúde",
    "Industrials": "Industrial",
    "Real Estate": "Reits-USA",
    "Technology": "Tecnologia",
    "Utilities": "Elétricas" # Renomeando Utilidades Públicas para Elétricas
}

FII_SECTOR_MAP = {
    'REIT - Industrial': 'Logística',
    'REIT - Retail': 'Shoppings',
    'REIT - Diversified': 'Renda Urbana / Híbrido',
    'Asset Management': 'Recebíveis',
    'REIT - Office': 'Lajes Corporativas',
    'REIT - Specialty': 'Renda Urbana',
    'REIT - Hotel & Motel': 'Hotéis',
    'REIT - Residential': 'Residencial'
}

FII_TICKER_OVERRIDE = {
    'PVBI11.SA': 'Lajes Corporativas',
    'MCRE11.SA': 'Recebíveis',
    'KNHF11.SA': 'Hedge Funds',
    'KNCA11.SA': 'Recebíveis',
    'RBRY11.SA': 'Recebíveis',
    'FATN11.SA': 'Renda Urbana',
    'TRXF11.SA': 'Renda Urbana'
}

@st.cache_data(ttl=300)
def fetch_asset_sectors(df_assets_tuple, refresh_id=0):
    """
    Recebe uma tupla de (tickers, asset_types) e retorna um dicionário mapeando ticker -> setor.
    Usamos tupla para ser hashable pelo st.cache_data.
    """
    tickers, asset_types = df_assets_tuple
    sectors = {}
    for ticker, a_type in zip(tickers, asset_types):
        
        if ticker in sectors:
            continue
            
        if a_type == 'Cripto':
            sectors[ticker] = 'Criptomoedas'
        elif a_type == 'Renda Fixa':
            sectors[ticker] = 'Renda Fixa'
        else:
            try:
                info = yf.Ticker(ticker).info
                raw_sector = info.get('sector', 'Outros')
                raw_industry = info.get('industry', 'N/A')
                
                # Se for FII, tentamos uma classificação mais granular via Ticker ou Industry
                if a_type == 'Fiis':
                    if ticker in FII_TICKER_OVERRIDE:
                        sectors[ticker] = FII_TICKER_OVERRIDE[ticker]
                    else:
                        sectors[ticker] = FII_SECTOR_MAP.get(raw_industry, 'Fiis - Outros')
                    continue

                raw_industry_lower = raw_industry.lower()
                
                # Regras refinadas via Industry
                if raw_sector == 'Utilities':
                    # Verifica se atua com eletricidade/energia renovável (geração, transmissão, etc)
                    if any(term in raw_industry for term in ['power', 'electric', 'renewable', 'utility']):
                        sectors[ticker] = "Elétricas"
                    else:
                        # Para água/saneamento que também entram em Utilities no YF
                        sectors[ticker] = "Saneamento / Outras Utilidades"
                        
                elif raw_sector == 'Energy':
                    # Petróleo e Gás
                    if any(term in raw_industry for term in ['oil', 'gas', 'exploration', 'drilling', 'petroleum']):
                        sectors[ticker] = "Óleo e Gás"
                    else:
                        sectors[ticker] = "Energia (Outros)" # Ex: Carvão/Mineração não petroleira
                        
                elif raw_sector in ['Industrials', 'Financial Services']:
                    # Captura Holdings como a Itaúsa que caem no setor Industrial ou Financeiro 
                    if any(term in raw_industry for term in ['conglomerate', 'holding']):
                        sectors[ticker] = "Holdings"
                    else:
                        sectors[ticker] = SECTOR_TRANSLATION.get(raw_sector, raw_sector)
                else:
                    # Mapeamento padrão pelo macro-setor
                    sectors[ticker] = SECTOR_TRANSLATION.get(raw_sector, raw_sector)
            except Exception:
                sectors[ticker] = 'Outros'
    return sectors

@st.cache_data(ttl=3600)
def get_index_history(ticker, period="1y"):
    """Busca histórico de um índice via yfinance."""
    try:
        data = yf.Ticker(ticker).history(period=period)
        if not data.empty:
            return data['Close']
    except Exception as e:
        print(f"Erro ao buscar histórico de {ticker}: {e}")
    return pd.Series()

@st.cache_data(ttl=3600)
def get_bcb_history(code, start_date):
    """Busca histórico de uma série do BCB (SGS)."""
    import requests
    from datetime import datetime
    
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            df['data'] = pd.to_datetime(df['data'], dayfirst=True)
            df['valor'] = df['valor'].astype(float)
            
            # Filtra pela data de início
            start_dt = pd.to_datetime(start_date)
            df = df[df['data'] >= start_dt]
            return df.set_index('data')['valor']
    except Exception as e:
        print(f"Erro ao buscar BCB {code}: {e}")
    return pd.Series()

def get_major_indices_history(months=18):
    """Retorna um DataFrame com o histórico acumulado dos principais índices."""
    from datetime import datetime, timedelta
    start_date = (datetime.now() - timedelta(days=months*31)).strftime('%Y-%m-%d')
    
    # 1. IBOV
    ibov = get_index_history("^BVSP", period="2y")
    
    # 2. IFIX
    # Usamos o XFIX11.SA (Trend ETF IFIX) como proxy altamente fidedigna pois IFIX.SA quebrou no YahooFinance
    ifix = get_index_history("XFIX11.SA", period="2y")
    
    # 3. CDI (4391) e 4. IPCA (432 - Número Índice)
    cdi_mensal = get_bcb_history(4391, start_date)
    ipca_mensal = get_bcb_history(432, start_date)
    
    return {
        'ibov': ibov,
        'ifix': ifix,
        'cdi': cdi_mensal,
        'ipca': ipca_mensal
    }
