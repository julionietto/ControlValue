import yfinance as yf  # type: ignore # pyrefly: ignore[missing-import]
import pandas as pd  # type: ignore
# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
from utils.refresh_manager import is_market_open
import socket
from zoneinfo import ZoneInfo

# Força timeout agressivo a nível de socket para evitar travamentos de 60 segundos em firewalls / IP blocking do Yahoo
socket.setdefaulttimeout(5.0)

@st.cache_data(ttl=300)
def _fetch_prices_batch(tickers_tuple, refresh_id=0):
    prices = {}
    if not tickers_tuple:
        return prices
        
    tickers_list = list(set(tickers_tuple))
    
    # 1. Busca Primária via fast_info em paralelo (altamente precisa para cotações mais recentes como ARE $52.72)
    import concurrent.futures
    def fetch_fast(t):
        try:
            val = float(yf.Ticker(t).fast_info.get('lastPrice', 0.0))
            return t, val if (not pd.isna(val) and val > 0.0) else 0.0
        except Exception:
            return t, 0.0

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_fast, tickers_list)
        for t, val in results:
            if val > 0.0:
                prices[t] = val

    # 2. Busca Secundária via yf.download (fallback caso fast_info falhe para algum ticker)
    missing_tickers = [t for t in tickers_list if prices.get(t, 0.0) <= 0.0]
    if missing_tickers:
        tickers_str = " ".join(missing_tickers)
        try:
            data = yf.download(tickers_str, period="5d", threads=True, progress=False, ignore_tz=True)
            if not data.empty:
                close_df = data['Close'] if 'Close' in data else data
                for ticker in missing_tickers:
                    val = 0.0
                    try:
                        if len(missing_tickers) == 1:
                            valid_series = close_df.dropna() if isinstance(close_df, pd.Series) else close_df.iloc[:, 0].dropna()
                            if not valid_series.empty:
                                val = float(valid_series.iloc[-1])
                        else:
                            if ticker in close_df:
                                series_t = close_df[ticker].dropna()
                                if not series_t.empty:
                                    val = float(series_t.iloc[-1])
                    except Exception as e:
                        import logging
                        logging.warning(f"Erro no fallback do ticker {ticker}: {e}")
                    if val > 0.0:
                        prices[ticker] = val
        except Exception as e:
            print(f"Falha YF Download Fallback: {e}")
            
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
    Persiste em session_state e possui valor de fallback em caso de falha.
    """
    current_val = st.session_state.get('last_btc_rate', 0.0)
    try:
        data = yf.Ticker("BTC-USD").history(period="5d")
        val = 0.0
        if not data.empty:
            val = float(data['Close'].iloc[-1])
        else:
            try:
                val = float(yf.Ticker("BTC-USD").fast_info['lastPrice'])
            except:
                val = 0.0
        
        if val > 0:
            st.session_state.last_btc_rate = val
        return val if val > 0 else (current_val if current_val > 0 else 60000.0)
    except Exception as e:
        print(f"Erro ao buscar cotação BTC/USD: {e}")
        return current_val if current_val > 0 else 60000.0

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
        return val if val > 0 else (current_val if current_val > 0 else 130000.0)
    except Exception as e:
        print(f"Erro ao buscar pontuação do IBOV: {e}")
        return current_val if current_val > 0 else 130000.0

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
    'FATN11.SA': 'Lajes Corporativas', 'PVBI11.SA': 'Lajes Corporativas', 'HGRE11.SA': 'Lajes Corporativas', 'KNRI11.SA': 'Lajes Corporativas', 'BRCR11.SA': 'Lajes Corporativas', 'VINO11.SA': 'Lajes Corporativas', 'RBRP11.SA': 'Lajes Corporativas', 'RECT11.SA': 'Lajes Corporativas', 'SARE11.SA': 'Lajes Corporativas',
    'MCRE11.SA': 'Recebíveis', 'KNCA11.SA': 'Recebíveis', 'RBRY11.SA': 'Recebíveis', 'KNIP11.SA': 'Recebíveis', 'KNCR11.SA': 'Recebíveis', 'IRDM11.SA': 'Recebíveis', 'CPTS11.SA': 'Recebíveis', 'HCTR11.SA': 'Recebíveis', 'MXRF11.SA': 'Recebíveis', 'VGHF11.SA': 'Recebíveis', 'CVBI11.SA': 'Recebíveis', 'HGCR11.SA': 'Recebíveis', 'MCCI11.SA': 'Recebíveis', 'URPR11.SA': 'Recebíveis', 'KNSC11.SA': 'Recebíveis', 'RBRR11.SA': 'Recebíveis', 'KNHY11.SA': 'Recebíveis', 'BARR11.SA': 'Recebíveis', 'VRTA11.SA': 'Recebíveis', 'HABT11.SA': 'Recebíveis', 'KNUQ11.SA': 'Recebíveis',
    'HGLG11.SA': 'Logística', 'BTLG11.SA': 'Logística', 'XPLG11.SA': 'Logística', 'VILG11.SA': 'Logística', 'ALZR11.SA': 'Logística', 'GGRC11.SA': 'Logística', 'LVBI11.SA': 'Logística', 'BRCO11.SA': 'Logística', 'RBRL11.SA': 'Logística', 'HSLG11.SA': 'Logística', 'GALG11.SA': 'Logística',
    'VISC11.SA': 'Shoppings', 'XPML11.SA': 'Shoppings', 'HSML11.SA': 'Shoppings', 'MALL11.SA': 'Shoppings', 'HGBS11.SA': 'Shoppings', 'VSHO11.SA': 'Shoppings',
    'TRXF11.SA': 'Renda Urbana', 'HGRU11.SA': 'Renda Urbana', 'RBVA11.SA': 'Renda Urbana', 'GARE11.SA': 'Renda Urbana',
    'KNHF11.SA': 'Hedge Funds', 'VGIA11.SA': 'Fiagro', 'SNAG11.SA': 'Fiagro', 'RZAG11.SA': 'Fiagro', 'CPTR11.SA': 'Fiagro'
}

STOCK_TICKER_OVERRIDE = {
    'PETR4.SA': 'Óleo e Gás', 'PETR3.SA': 'Óleo e Gás', 'PRIO3.SA': 'Óleo e Gás', 'RRRP3.SA': 'Óleo e Gás', 'RECV3.SA': 'Óleo e Gás', 'ENAT3.SA': 'Óleo e Gás',
    'VALE3.SA': 'Materiais Básicos', 'CSNA3.SA': 'Materiais Básicos', 'USIM5.SA': 'Materiais Básicos', 'GGBR4.SA': 'Materiais Básicos', 'GOAU4.SA': 'Materiais Básicos', 'SUZB3.SA': 'Materiais Básicos', 'KLBN11.SA': 'Materiais Básicos', 'CBAV3.SA': 'Materiais Básicos',
    'ITUB4.SA': 'Serviços Financeiros', 'ITUB3.SA': 'Serviços Financeiros', 'BBDC4.SA': 'Serviços Financeiros', 'BBDC3.SA': 'Serviços Financeiros', 'BBAS3.SA': 'Serviços Financeiros', 'SANB11.SA': 'Serviços Financeiros', 'BPAC11.SA': 'Serviços Financeiros', 'B3SA3.SA': 'Serviços Financeiros', 'CXSE3.SA': 'Seguros', 'BBSE3.SA': 'Seguros', 'PSSA3.SA': 'Seguros', 'IRBR3.SA': 'Seguros',
    'WEGE3.SA': 'Industrial', 'EMBR3.SA': 'Industrial', 'TUPY3.SA': 'Industrial', 'POMO4.SA': 'Industrial', 'RAPT4.SA': 'Industrial',
    'ELET3.SA': 'Elétricas', 'ELET6.SA': 'Elétricas', 'EQTL3.SA': 'Elétricas', 'TAEE11.SA': 'Elétricas', 'TRPL4.SA': 'Elétricas', 'CPLE6.SA': 'Elétricas', 'CMIG4.SA': 'Elétricas', 'EGIE3.SA': 'Elétricas', 'ENBR3.SA': 'Elétricas', 'ALUP11.SA': 'Elétricas', 'AURE3.SA': 'Elétricas', 'NEOE3.SA': 'Elétricas', 'CPFE3.SA': 'Elétricas',
    'SBSP3.SA': 'Saneamento / Outras Utilidades', 'CSMG3.SA': 'Saneamento / Outras Utilidades', 'SAPR11.SA': 'Saneamento / Outras Utilidades', 'SAPR4.SA': 'Saneamento / Outras Utilidades',
    'RENT3.SA': 'Consumo Cíclico', 'VAMO3.SA': 'Consumo Cíclico', 'LREN3.SA': 'Consumo Cíclico', 'ALOS3.SA': 'Consumo Cíclico', 'SOMA3.SA': 'Consumo Cíclico', 'ARZZ3.SA': 'Consumo Cíclico', 'CEAB3.SA': 'Consumo Cíclico', 'AMOB3.SA': 'Consumo Cíclico', 'SMFT3.SA': 'Consumo Cíclico', 'COGN3.SA': 'Educação', 'YDUQ3.SA': 'Educação',
    'RADL3.SA': 'Consumo Defensivo', 'CRFB3.SA': 'Consumo Defensivo', 'ASAI3.SA': 'Consumo Defensivo', 'NTCO3.SA': 'Consumo Defensivo', 'ABEV3.SA': 'Consumo Defensivo', 'JBSS3.SA': 'Consumo Defensivo', 'MRFG3.SA': 'Consumo Defensivo', 'BEEF3.SA': 'Consumo Defensivo', 'BRFS3.SA': 'Consumo Defensivo', 'SMTO3.SA': 'Consumo Defensivo',
    'HYPE3.SA': 'Saúde', 'FLRY3.SA': 'Saúde', 'RDOR3.SA': 'Saúde', 'HAPV3.SA': 'Saúde', 'MATD3.SA': 'Saúde', 'PNVL3.SA': 'Saúde', 'ODPV3.SA': 'Saúde',
    'VIVT3.SA': 'Serviços de Comunicação', 'TIMS3.SA': 'Serviços de Comunicação',
    'EZTC3.SA': 'Construção Civil', 'CYRE3.SA': 'Construção Civil', 'MRVE3.SA': 'Construção Civil', 'TEND3.SA': 'Construção Civil', 'DIRR3.SA': 'Construção Civil',
    'ITSA4.SA': 'Holdings'
}

@st.cache_data(ttl=300)
def _fetch_single_sector(ticker, a_type):
    if a_type == 'Cripto':
        return 'Criptomoedas'
    elif a_type == 'Renda Fixa':
        return 'Renda Fixa'
    elif a_type == 'Fundo CETIP':
        return 'Fundo CETIP'
    elif a_type == 'ETF':
        return 'ETF'
    elif a_type == 'Reits':
        return 'Reits-USA'
    else:
        # Prioridade 1: Dicionários locais de Override (salva a pátria se YF falhar ou não tiver os dados)
        if a_type == 'Fiis' and ticker in FII_TICKER_OVERRIDE:
            return FII_TICKER_OVERRIDE[ticker]
        if a_type == 'Ações' and ticker in STOCK_TICKER_OVERRIDE:
            return STOCK_TICKER_OVERRIDE[ticker]

        # Prioridade 2: Tentar Yahoo Finance Direto (Evita o .info bugado do yfinance recente)
        import requests
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=assetProfile"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        
        raw_sector = 'Outros'
        raw_industry = 'N/A'
        
        try:
            resp = requests.get(url, headers=headers, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                res = data.get('quoteSummary', {}).get('result', [])
                if res and len(res) > 0 and res[0] is not None:
                    profile = res[0].get('assetProfile', {})
                    if profile:
                        raw_sector = profile.get('sector', 'Outros')
                        raw_industry = profile.get('industry', 'N/A')
        except Exception as e:
            pass # Silencioso, tentará o fallback se falhar

        if a_type == 'Fiis':
            return FII_SECTOR_MAP.get(raw_industry, 'Fiis - Outros')

        raw_industry_lower = raw_industry.lower()
        
        if raw_sector == 'Utilities':
            if any(term in raw_industry_lower for term in ['power', 'electric', 'renewable', 'utility']):
                return "Elétricas"
            else:
                return "Saneamento / Outras Utilidades"
                
        elif raw_sector == 'Energy':
            if any(term in raw_industry_lower for term in ['oil', 'gas', 'exploration', 'drilling', 'petroleum']):
                return "Óleo e Gás"
            else:
                return "Energia (Outros)"
                
        elif raw_sector in ['Industrials', 'Financial Services']:
            if any(term in raw_industry_lower for term in ['conglomerate', 'holding']):
                return "Holdings"
            else:
                return SECTOR_TRANSLATION.get(raw_sector, raw_sector)
        else:
            return SECTOR_TRANSLATION.get(raw_sector, raw_sector)

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
            
        if a_type in ['Cripto', 'Renda Fixa', 'Fundo CETIP']:
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
        # Adiciona User-Agent completo e Accept header para evitar bloqueios e erros 406
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        response = requests.get(url, timeout=30, headers=headers)
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
    """Busca a série histórica do CDI (SGS 12) dos últimos 5 anos e armazena em cache global."""
    from datetime import datetime, timedelta
    # O BCB limita consultas de séries diárias a janelas de no máximo 10 anos.
    # Usamos 5 anos como um compromisso entre performance e histórico.
    start_dt = (datetime.now() - timedelta(days=1825)).strftime('%Y-%m-%d')
    series = get_bcb_history(12, start_dt)
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
    """Retorna a série de CDI fatiada do master ou busca especificamente se necessário."""
    dt = pd.to_datetime(start_date).tz_localize(None)
    
    # 1. Tentar usar o Master Cache
    master = get_master_cdi_history()
    if not master.empty:
        # Verifica se o Master Cache cobre a data solicitada (dt >= data inicial do cache)
        if master.index.min() <= dt:
            sliced = master[master.index >= dt]
            if not sliced.empty:
                return sliced
            
    # 2. Fallback: Busca específica se o master falhar ou se a data for anterior a 2010
    series = get_bcb_history(12, start_date)
    if not series.empty:
        return (1 + series / 100)
    return pd.Series()

def get_usd_brl_history(start_date):
    """Retorna a série de USD/BRL fatiada do master ou busca especificamente se necessário."""
    dt = pd.to_datetime(start_date).tz_localize(None)
    
    # 1. Tentar usar o Master Cache
    master = get_master_usd_history()
    if not master.empty:
        # Verifica se o Master Cache cobre a data solicitada
        if master.index.min() <= dt:
            sliced = master[master.index >= dt]
            if not sliced.empty:
                return sliced
            
    # 2. Fallback: Busca específica
    try:
        data = yf.download("BRL=X", start=start_date, progress=False)
        if not data.empty:
            data.index = pd.to_datetime(data.index).tz_localize(None)
            if 'Close' in data:
                return data['Close']
            return data.iloc[:, 0]
    except Exception as e:
        print(f"Erro ao buscar fallback USD: {e}")
    return pd.Series()

def _send_smtp_email(to_email, subject, html_content):
    """Função auxiliar centralizada para envio de e-mails via SMTP Gmail."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import os
    # pyrefly: ignore [missing-import]
    import streamlit as st
    
    # Busca credenciais de forma idêntica ao que funciona na recuperação de senha
    smtp_email = ""
    smtp_password = ""
    try:
        if "SMTP_EMAIL" in st.secrets:
            smtp_email = st.secrets["SMTP_EMAIL"]
            smtp_password = st.secrets["SMTP_PASSWORD"]
    except:
        pass
        
    if not smtp_email or not smtp_password:
        smtp_email = os.getenv("SMTP_EMAIL", "controlvalueoficial@gmail.com")
        smtp_password = os.getenv("SMTP_PASSWORD", "")

    if not smtp_email or not smtp_password:
        print("SMTP Credentials missing")
        return False, "Credenciais SMTP não encontradas."
        
    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From'] = smtp_email
    msg['To'] = to_email
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.send_message(msg)
        server.quit()
        return True, "E-mail enviado com sucesso."
    except Exception as e:
        print(f"SMTP erro: {e}")
        return False, str(e)

def send_password_reset_email(to_email, reset_link):
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
            <h2 style="color: #3b82f6; text-align: center;">ControlValue</h2>
            <p>Olá,</p>
            <p>Recebemos uma solicitação para redefinir a senha da sua conta.</p>
            <p>Para redefinir sua senha, clique no botão abaixo (válido por 30 minutos):</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}" style="background-color: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Redefinir Minha Senha</a>
            </div>
            <p style="font-size: 12px; color: #999;">Ou copie e cole este link no seu navegador:</p>
            <p style="font-size: 12px; color: #999; word-break: break-all;">{reset_link}</p>
        </div>
      </body>
    </html>
    """
    return _send_smtp_email(to_email, "Recuperação de Senha - ControlValue", html)

def send_exception_report_email(exception_details):
    # pyrefly: ignore [missing-import]
    import streamlit as st
    user_info = ""
    if 'user_id' in st.session_state:
        user_info = f"<p><b>User ID:</b> {st.session_state.user_id}</p>"
    
    html = f"""
    <html>
      <body style="font-family: 'Courier New', Courier, monospace; color: #333; background-color: #f9f9f9; padding: 20px;">
        <div style="max-width: 800px; margin: 0 auto; padding: 20px; border: 2px solid #ff4b4b; border-radius: 10px; background-color: white;">
            <h2 style="color: #ff4b4b; text-align: center;">🚨 Exception Capturada</h2>
            <p>Ocorreu um erro inesperado na aplicação ControlValue.</p>
            {user_info}
            <hr style="border: 0; border-top: 1px solid #eee;">
            <p><b>Detalhes da Exception:</b></p>
            <pre style="background-color: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap;">{exception_details}</pre>
        </div>
      </body>
    </html>
    """
    target_email = os.getenv("ADMIN_EMAIL", os.getenv("SMTP_EMAIL", "controlvalueoficial@gmail.com"))
    success, msg = _send_smtp_email(target_email, "Exception capturada no App ControlValue", html)
    return success

def fetch_investidor10_proventos(tickers_with_types):
    """
    Busca dados de proventos provisionados via scraping do Investidor10.
    Recebe uma lista de dicionários [{'ticker': 'PETR4', 'type': 'Ações'}, ...]
    Retorna (DataFrame, error_message, raw_json_list).
    """
    import os
    import time
    from datetime import datetime
    import pandas as pd
    # pyrefly: ignore [missing-import]
    from bs4 import BeautifulSoup
    
    if not tickers_with_types:
        return pd.DataFrame(), "", []
        
    type_to_endpoint = {
        'Ações': 'acoes',
        'Fiis': 'fiis',
        'ETF': 'etfs',
        'Stocks': 'stocks',
        'Reits': 'reits'
    }

    all_dividends = []
    full_raw_response = []
    
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    try:
        # pyrefly: ignore [missing-import]
        from curl_cffi import requests as cffi_requests
        
        custom_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://investidor10.com.br/",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1"
        }
        
        session = cffi_requests.Session(impersonate='chrome120')
        session.headers.update(custom_headers)
        
        # Acessa a home primeiro para pegar cookies e passar pelo Cloudflare
        try:
            session.get("https://investidor10.com.br/", timeout=15)
            import random
            time.sleep(random.uniform(1.0, 2.0))
        except:
            pass
            
    except Exception as e:
        print(f"Erro ao iniciar curl_cffi session: {e}")
        return pd.DataFrame(), "", []

    for item in tickers_with_types:
        t = item['ticker']
        a_type = item['type']
        
        clean_t = t.strip().upper().replace(".SA", "")
        if not clean_t:
            continue
            
        ep = type_to_endpoint.get(a_type, 'acoes')
        
        # Caso especial: muitas BDRs cadastradas como Stocks caem na rota /bdrs/
        # Vamos tentar a rota original primeiro
        urls_to_try = [f"https://investidor10.com.br/{ep}/{clean_t.lower()}/"]
        if a_type == 'Stocks':
            urls_to_try.append(f"https://investidor10.com.br/bdrs/{clean_t.lower()}/")
            
        success = False
        
        for url in urls_to_try:
            if success:
                break
                
            try:
                response = session.get(url, timeout=15)
                if response.status_code == 200:
                    html = response.text
                    soup = BeautifulSoup(html, "html.parser")
                    
                    table = soup.find('table', id='table-dividends-history')
                    if not table:
                        full_raw_response.append({clean_t: "Tabela de dividendos não encontrada na página."})
                        success = True # Pagina carregou mas não tem dividendos
                        break
                        
                    rows = table.find('tbody').find_all('tr')
                    full_raw_response.append({clean_t: f"Tabela encontrada com {len(rows)} proventos históricos/futuros."})
                    
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 4:
                            tipo_prov = cols[0].text.strip()
                            dt_com_str = cols[1].text.strip()
                            dt_pag_str = cols[2].text.strip()
                            valor_str = cols[3].text.strip().replace('R$', '').replace('$', '').strip()
                            
                            if dt_pag_str in ['N/A', '-', '']:
                                continue
                                
                            try:
                                dt_pag_obj = datetime.strptime(dt_pag_str, '%d/%m/%Y')
                            except:
                                continue
                                
                            if dt_pag_obj >= hoje:
                                try:
                                    valor = float(valor_str.replace('.', '').replace(',', '.'))
                                except:
                                    valor = 0.0
                                    
                                if valor > 0:
                                    all_dividends.append({
                                        'Ativo': clean_t,
                                        'Tipo': tipo_prov,
                                        'Data Com': dt_com_str,
                                        'Data Pagamento': dt_pag_str,
                                        'Valor': valor,
                                        'dt_pag_raw': dt_pag_obj
                                    })
                    success = True
                else:
                    full_raw_response.append({clean_t: f"Erro HTTP {response.status_code}"})
            except Exception as e:
                print(f"Erro ao buscar {clean_t} no Investidor10: {e}")
                full_raw_response.append({clean_t: f"Exception: {str(e)}"})
                
        import random
        time.sleep(random.uniform(1.5, 3.5))

    if not all_dividends:
        return pd.DataFrame(), "", full_raw_response
        
    df = pd.DataFrame(all_dividends)
    
    # Agrupa por chaves únicas e soma o valor para evitar duplicidades no mesmo evento (Ex: TAEE11)
    # Isso resolve o problema de múltiplos lançamentos para o mesmo provento no Investidor10
    df = df.groupby(['Ativo', 'Tipo', 'Data Com', 'Data Pagamento'], as_index=False).agg({
        'Valor': 'sum',
        'dt_pag_raw': 'first'
    })
    
    df = df.sort_values(by=['dt_pag_raw', 'Ativo'], ascending=[True, True])
    df = df.drop(columns=['dt_pag_raw'])
    
    return df, "", full_raw_response

def fetch_option_strike_opcoes_net(ticker):
    """
    Busca o valor atualizado do strike de uma opção no portal opcoes.net.br.
    Retorna o valor como float ou None se não encontrado.
    """
    import requests
    import re
    
    url = f"https://opcoes.net.br/{ticker}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # Tenta extrair do título da página via regex
            # Ex: <title>EGIEE407 - Strike R$ 40,25 - Vencimento 15/05/2026</title>
            match = re.search(r"Strike R\$ ([\d,.]+)", response.text)
            if match:
                val_str = match.group(1).replace('.', '').replace(',', '.')
                return float(val_str)
    except Exception as e:
        print(f"Erro ao buscar strike de {ticker}: {e}")
        
    return None
