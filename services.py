import yfinance as yf
import pandas as pd
import streamlit as st
from utils.refresh_manager import is_market_open
import socket
from zoneinfo import ZoneInfo

# Força timeout agressivo a nível de socket para evitar travamentos de 60 segundos em firewalls / IP blocking do Yahoo
socket.setdefaulttimeout(3.0)

@st.cache_data(ttl=300)
def _fetch_prices_batch(tickers_tuple, refresh_id=0):
    prices = {}
    if not tickers_tuple:
        return prices
        
    tickers_list = list(set(tickers_tuple))
    tickers_str = " ".join(tickers_list)
    
    try:
        # yf.download agrupa todas as requisições, evitando bloqueios na AWS/Streamlit Cloud
        data = yf.download(tickers_str, period="1d", threads=True, progress=False, ignore_tz=True)
        
        if not data.empty:
            if 'Close' in data:
                close_df = data['Close']
            else:
                close_df = data
                
            for ticker in tickers_list:
                val = 0.0
                try:
                    if len(tickers_list) == 1:
                        import numbers
                        val_raw = close_df.iloc[-1]
                        if isinstance(val_raw, numbers.Number):
                            val = float(val_raw)
                        else:
                            val = float(val_raw.iloc[0] if hasattr(val_raw, 'iloc') else 0.0)
                    else:
                        if ticker in close_df:
                            val = float(close_df[ticker].iloc[-1])
                except Exception:
                    pass
                
                prices[ticker] = val
                
    except Exception as e:
        print(f"Falha YF Download: {e}")
        
    # Identificar quais falharam no download em batch ou retornaram <= 0
    missing_tickers = [t for t in tickers_list if pd.isna(prices.get(t, 0.0)) or prices.get(t, 0.0) <= 0.0]
    
    # Resgate paralelo incrivelmente mais rápido para ativos que o yf.download não capturou
    if missing_tickers:
        import concurrent.futures
        
        def fetch_fast_info(t):
            try:
                return t, float(yf.Ticker(t).fast_info.get('lastPrice', 0.0))
            except Exception:
                return t, 0.0

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(fetch_fast_info, missing_tickers)
            for t, val in results:
                prices[t] = val
                
    # Assegura que sempre retornamos aquilo que foi pedido
    for t in tickers_tuple:
        if t not in prices:
            prices[t] = 0.0
            
    return prices

def fetch_current_prices(tickers, refresh_id=0):
    """
    Busca os preços atuais para uma lista de tickers usando yfinance em Lote (Batch).
    Retorna um dicionário mapeando o ticker para seu preço atual.
    """
    if not tickers:
        return {}
    
    # Tupla é hashable permitindo que o Streamlit faça cache de chamadas semelhantes
    return _fetch_prices_batch(tuple(tickers), refresh_id)

@st.cache_data(ttl=300)
def get_usd_brl_rate(refresh_id=0, is_first_load=False):
    """
    Busca a cotação atual do Dólar em Reais usando o ticker BRL=X.
    Respeita as regras de mercado BR, exceto na primeira carga após o login.
    """
    current_val = st.session_state.get('last_usd_rate', 0.0)
    
    # Se o mercado está fechado e já temos um valor válido (diferente de 0), usamos o cache
    if not is_market_open('BR') and not is_first_load and current_val > 0:
        return current_val

    try:
        # Usamos period="5d" para garantir que pegamos o último fechamento válido em noites/finais de semana
        data = yf.Ticker("BRL=X").history(period="5d")
        val = 0.0
        if not data.empty:
            val = float(data['Close'].iloc[-1])
        else:
            try:
                val = float(yf.Ticker("BRL=X").fast_info['lastPrice'])
            except:
                val = 0.0
        
        if val > 0:
            st.session_state.last_usd_rate = val
        return val if val > 0 else (current_val if current_val > 0 else 5.0)
    except Exception as e:
        print(f"Erro ao buscar cotação USD/BRL: {e}")
        return current_val if current_val > 0 else 5.0

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
def get_ibov(refresh_id=0, is_first_load=False):
    """
    Busca a pontuação atual do IBOVESPA usando o ticker ^BVSP.
    Respeita as regras de mercado BR, exceto na primeira carga após o login.
    """
    current_val = st.session_state.get('last_ibov_points', 0.0)
    
    # Se o mercado está fechado e já temos um valor válido (diferente de 0), usamos o cache
    if not is_market_open('BR') and not is_first_load and current_val > 0:
        return current_val

    try:
        # Usamos period="5d" para garantir que pegamos o último fechamento válido em noites/finais de semana
        data = yf.Ticker("^BVSP").history(period="5d")
        val = 0.0
        if not data.empty:
            val = float(data['Close'].iloc[-1])
        else:
            try:
                val = float(yf.Ticker("^BVSP").fast_info['lastPrice'])
            except:
                val = 0.0
        
        if val > 0:
            st.session_state.last_ibov_points = val
        return val if val > 0 else current_val
    except Exception as e:
        print(f"Erro ao buscar pontuação do IBOV: {e}")
        return current_val

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
def _fetch_single_sector(ticker, a_type):
    if a_type == 'Cripto':
        return 'Criptomoedas'
    elif a_type == 'Renda Fixa':
        return 'Renda Fixa'
    else:
        try:
            info = yf.Ticker(ticker).info
            raw_sector = info.get('sector', 'Outros')
            raw_industry = info.get('industry', 'N/A')
            
            if a_type == 'Fiis':
                if ticker in FII_TICKER_OVERRIDE:
                    return FII_TICKER_OVERRIDE[ticker]
                else:
                    return FII_SECTOR_MAP.get(raw_industry, 'Fiis - Outros')

            raw_industry_lower = raw_industry.lower()
            
            if raw_sector == 'Utilities':
                if any(term in raw_industry for term in ['power', 'electric', 'renewable', 'utility']):
                    return "Elétricas"
                else:
                    return "Saneamento / Outras Utilidades"
                    
            elif raw_sector == 'Energy':
                if any(term in raw_industry for term in ['oil', 'gas', 'exploration', 'drilling', 'petroleum']):
                    return "Óleo e Gás"
                else:
                    return "Energia (Outros)"
                    
            elif raw_sector in ['Industrials', 'Financial Services']:
                if any(term in raw_industry for term in ['conglomerate', 'holding']):
                    return "Holdings"
                else:
                    return SECTOR_TRANSLATION.get(raw_sector, raw_sector)
            else:
                return SECTOR_TRANSLATION.get(raw_sector, raw_sector)
        except Exception:
            return 'Outros'

def fetch_asset_sectors(df_assets_tuple, is_auto_refresh=False):
    """
    Recebe uma tupla de (tickers, asset_types) e retorna um dicionário mapeando ticker -> setor.
    """
    if 'sector_cache_dict' not in st.session_state:
        st.session_state.sector_cache_dict = {}
        
    tickers, asset_types = df_assets_tuple
    sectors = {}
    for ticker, a_type in zip(tickers, asset_types):
        if ticker in sectors:
            continue
            
        if a_type in ['Cripto', 'Renda Fixa']:
            sectors[ticker] = _fetch_single_sector(ticker, a_type)
            st.session_state.sector_cache_dict[ticker] = sectors[ticker]
        else:
            if ticker in st.session_state.sector_cache_dict:
                sectors[ticker] = st.session_state.sector_cache_dict[ticker]
            else:
                if is_auto_refresh:
                    fetched = _fetch_single_sector(ticker, a_type)
                    sectors[ticker] = fetched
                    st.session_state.sector_cache_dict[ticker] = fetched
                else:
                    sectors[ticker] = "Pendente (Auto-update)"
                    
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
    
    # Converte start_date (YYYY-MM-DD) para formato BCB (DD/MM/YYYY)
    try:
        dt_obj = datetime.strptime(start_date, '%Y-%m-%d')
        bcb_date = dt_obj.strftime('%d/%m/%Y')
    except:
        sp_tz = ZoneInfo("America/Sao_Paulo")
        bcb_date = datetime.now(sp_tz).strftime('01/01/%Y') # fallback

    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json&dataInicial={bcb_date}"
    
    try:
        # Adiciona User-Agent para evitar bloqueios triviais
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=15, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if not data:
                return pd.Series()
                
            df = pd.DataFrame(data)
            df['data'] = pd.to_datetime(df['data'], dayfirst=True)
            df['valor'] = df['valor'].astype(float)
            
            # Filtra novamente em memória apenas por segurança (dataInicial garante a janela do servidor)
            start_dt = pd.to_datetime(start_date)
            df = df[df['data'] >= start_dt]
            return df.set_index('data')['valor']
        else:
            print(f"Erro BCB {code}: Status {response.status_code}")
    except Exception as e:
        print(f"Erro ao buscar BCB {code}: {e}")
    return pd.Series()

def get_major_indices_history(months=18):
    """Retorna um DataFrame com o histórico acumulado dos principais índices."""
    from datetime import datetime, timedelta
    sp_tz = ZoneInfo("America/Sao_Paulo")
    start_date = (datetime.now(sp_tz).replace(tzinfo=None) - timedelta(days=months*31)).strftime('%Y-%m-%d')
    
    # 1. IBOV
    ibov = get_index_history("^BVSP", period="2y")
    
    # 2. IFIX
    # Usamos o XFIX11.SA (Trend ETF IFIX) como proxy altamente fidedigna pois IFIX.SA quebrou no YahooFinance
    ifix = get_index_history("XFIX11.SA", period="2y")
    
    # 3. CDI (4391) e 4. IPCA (433 - Variação Mensal %)
    cdi_mensal = get_bcb_history(4391, start_date)
    ipca_mensal = get_bcb_history(433, start_date)
    
    return {
        'ibov': ibov,
        'ifix': ifix,
        'cdi': cdi_mensal,
        'ipca': ipca_mensal
    }

@st.cache_data(ttl=3600)
def get_asset_price_history(ticker, start_date):
    """Busca o histórico de fechamento diário de um ativo."""
    try:
        data = yf.download(ticker, start=start_date, progress=False)
        if not data.empty:
            if 'Close' in data:
                return data['Close']
            return data.iloc[:, 0] # Fallback
    except Exception as e:
        print(f"Erro ao buscar histórico de {ticker}: {e}")
    return pd.Series()

@st.cache_data(ttl=86400)
def get_master_cdi_history():
    """Busca a série histórica do CDI (SGS 12) desde 2000 e armazena em cache global."""
    series = get_bcb_history(12, "2000-01-01")
    if not series.empty:
        # Converte de % a.d. para fator diário (1 + taxa/100)
        return (1 + series / 100)
    return pd.Series()

@st.cache_data(ttl=86400)
def get_master_usd_history():
    """Busca a série histórica do USD/BRL desde 2000 e armazena em cache global."""
    try:
        data = yf.download("BRL=X", start="2000-01-01", progress=False)
        if not data.empty:
            # Garante que o índice seja datetime para facilitar o slicing
            data.index = pd.to_datetime(data.index).tz_localize(None)
            if 'Close' in data:
                return data['Close']
            return data.iloc[:, 0]
    except Exception as e:
        print(f"Erro ao buscar master USD: {e}")
    return pd.Series()

def get_daily_cdi_history(start_date):
    """Retorna a série de CDI fatiada a partir da data informada."""
    master = get_master_cdi_history()
    if not master.empty:
        dt = pd.to_datetime(start_date).tz_localize(None)
        return master[master.index >= dt]
    return pd.Series()

def get_usd_brl_history(start_date):
    """Retorna a série de USD/BRL fatiada a partir da data informada."""
    master = get_master_usd_history()
    if not master.empty:
        dt = pd.to_datetime(start_date).tz_localize(None)
        return master[master.index >= dt]
    return pd.Series()
