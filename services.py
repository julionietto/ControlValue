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
                except Exception as e:
                    import logging
                    logging.warning(f"Erro ao extrair valor do ticker {ticker}: {e}")
                
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

def send_password_reset_email(to_email, reset_link):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import os
    
    try:
        if "SMTP_EMAIL" in st.secrets:
            smtp_email = st.secrets["SMTP_EMAIL"]
            smtp_password = st.secrets["SMTP_PASSWORD"]
        else:
            smtp_email = os.getenv("SMTP_EMAIL", "")
            smtp_password = os.getenv("SMTP_PASSWORD", "")
    except Exception:
        smtp_email = os.getenv("SMTP_EMAIL", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        
    if not smtp_email or not smtp_password:
        print("SMTP Credentials missing")
        return False, "Servidor de e-mail não configurado pelo administrador."
        
    msg = MIMEMultipart("alternative")
    msg['Subject'] = "Recuperação de Senha - ControlValue"
    msg['From'] = smtp_email
    msg['To'] = to_email
    
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
            <h2 style="color: #3b82f6; text-align: center;">ControlValue</h2>
            <p>Olá,</p>
            <p>Recebemos uma solicitação para redefinir a senha da sua conta.</p>
            <p>Se você não fez essa solicitação, pode ignorar este e-mail com segurança.</p>
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
    
    msg.attach(MIMEText(html, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.send_message(msg)
        server.quit()
        return True, "E-mail enviado com sucesso."
    except Exception as e:
        print(f"SMTP erro: {e}")
        return False, f"Erro ao enviar e-mail."

def fetch_brapi_proventos(tickers_list):
    """
    Busca dados de proventos (dividendos/JCP) na API da Brapi.
    Retorna (DataFrame, error_message).
    """
    import requests
    import os
    import time
    
    try:
        if "BRAPI_TOKEN" in st.secrets:
            token = st.secrets["BRAPI_TOKEN"]
        else:
            token = os.getenv("BRAPI_TOKEN", "")
    except Exception:
        token = os.getenv("BRAPI_TOKEN", "")
        
    if not token or token == "":
        return None, "Token da Brapi não configurado. Por favor, adicione seu Token no arquivo .env (chave BRAPI_TOKEN)."
        
    if not tickers_list:
        return pd.DataFrame(), ""
        
    # Limpeza de Tickers: Brapi funciona melhor sem o sufixo .SA
    cleaned_tickers = []
    for t in tickers_list:
        clean_t = t.strip().upper()
        if clean_t.endswith(".SA"):
            clean_t = clean_t[:-3]
        if clean_t and clean_t not in cleaned_tickers:
            cleaned_tickers.append(clean_t)
            
    if not cleaned_tickers:
        return pd.DataFrame(), ""

    # Dividir em lotes de no máximo 15 tickers para evitar URLs muito longas ou erros de processamento em lote
    batch_size = 15
    batches = [cleaned_tickers[i:i + batch_size] for i in range(0, len(cleaned_tickers), batch_size)]
    
    all_dividends = []
    
    for batch in batches:
        tickers_str = ",".join(batch)
        url = f"https://brapi.dev/api/quote/{tickers_str}?dividends=true&token={token}"
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                for res in results:
                    ticker = res.get('symbol')
                    # Se o ticker retornar erro individual (ex: não encontrado), ele vem com erro no JSON
                    if res.get('error'):
                        continue
                        
                    div_data = res.get('dividendsData', {})
                    cash_divs = div_data.get('cashDividends', [])
                    
                    for d in cash_divs:
                        all_dividends.append({
                            'Ativo': ticker,
                            'Tipo': d.get('relatedTo', 'N/A'),
                            'Data Com': d.get('lastDatePrior', 'N/A'),
                            'Data Pagamento': d.get('paymentDate', 'N/A'),
                            'Valor': d.get('rate', 0.0)
                        })
            elif response.status_code == 401:
                return None, "Token da Brapi inválido ou expirado."
            elif response.status_code == 400:
                # Se o lote falhar, tentamos processar um por um deste lote para não perder tudo
                for single_t in batch:
                    single_url = f"https://brapi.dev/api/quote/{single_t}?dividends=true&token={token}"
                    try:
                        s_res = requests.get(single_url, timeout=10)
                        if s_res.status_code == 200:
                            s_data = s_res.json().get('results', [{}])[0]
                            if not s_data.get('error'):
                                s_divs = s_data.get('dividendsData', {}).get('cashDividends', [])
                                for d in s_divs:
                                    all_dividends.append({
                                        'Ativo': single_t,
                                        'Tipo': d.get('relatedTo', 'N/A'),
                                        'Data Com': d.get('lastDatePrior', 'N/A'),
                                        'Data Pagamento': d.get('paymentDate', 'N/A'),
                                        'Valor': d.get('rate', 0.0)
                                    })
                    except:
                        continue
            else:
                continue # Pula lotes com erro genérico
                
        except Exception as e:
            print(f"Erro no lote Brapi: {e}")
            continue

    if not all_dividends:
        return pd.DataFrame(), ""
        
    df = pd.DataFrame(all_dividends)
    
    # Converte Data Pagamento para datetime para filtragem
    df['dt_pag_raw'] = pd.to_datetime(df['Data Pagamento'], errors='coerce')
    df = df.dropna(subset=['dt_pag_raw'])
    
    # Filtro: Apenas proventos futuros (Data de Pagamento >= Hoje)
    from datetime import datetime
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    df = df[df['dt_pag_raw'] >= hoje]
    
    if df.empty:
        return pd.DataFrame(), ""

    # Formatação final para exibição
    df['Data Com'] = pd.to_datetime(df['Data Com'], errors='coerce').dt.strftime('%d/%m/%Y')
    df['Data Pagamento'] = df['dt_pag_raw'].dt.strftime('%d/%m/%Y')
    
    df = df[df['Valor'] > 0]
    df = df.drop_duplicates()
    df = df.sort_values(by=['dt_pag_raw', 'Ativo'], ascending=[True, True])
    
    return df, ""
