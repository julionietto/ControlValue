import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta

def get_bcb_history(code, start_date):
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data)
        df['data'] = pd.to_datetime(df['data'], dayfirst=True)
        df['valor'] = df['valor'].astype(float)
        start_dt = pd.to_datetime(start_date)
        df = df[df['data'] >= start_dt]
        return df.set_index('data')['valor']
    return pd.Series()

# Setup dates
hoje = pd.Timestamp.now().normalize()
months_14 = (hoje - timedelta(days=14*31)).strftime('%Y-%m-%d')
months_12 = (hoje - timedelta(days=12*31)).strftime('%Y-%m-%d')

print(f"Hoje: {hoje}")
print(f"Start 14m: {months_14}")
print(f"Start 12m: {months_12}")

# 1. IPCA (433)
ipca = get_bcb_history(433, months_14)
print("\nIPCA (433) - Last 15 points:")
print(ipca.tail(15))
if not ipca.empty:
    cum_ipca = (1 + ipca/100).cumprod()
    # Comparação: do ponto de 12 meses atrás até o último
    idx_12m = ipca.index[ipca.index >= pd.to_datetime(months_12)]
    if not idx_12m.empty:
        start_val = cum_ipca.get(idx_12m[0], 1.0)
        end_val = cum_ipca.iloc[-1]
        print(f"IPCA Acumulado 12m (Manual): {((end_val/start_val)-1)*100:.2f}%")

# 2. CDI (4391)
cdi = get_bcb_history(4391, months_14)
print("\nCDI (4391) - Last 15 points:")
print(cdi.tail(15))
if not cdi.empty:
    cum_cdi = (1 + cdi/100).cumprod()
    idx_12m = cdi.index[cdi.index >= pd.to_datetime(months_12)]
    if not idx_12m.empty:
        start_val = cum_cdi.get(idx_12m[0], 1.0)
        end_val = cum_cdi.iloc[-1]
        print(f"CDI Acumulado 12m (Manual): {((end_val/start_val)-1)*100:.2f}%")

# 4. IPCA Acumulado 12m (13522)
ipca_12m = get_bcb_history(13522, months_14)
print("\nIPCA Acumulado 12 meses (13522) - Last 5 points:")
print(ipca_12m.tail(5))

# 5. IPCA Index (432)
ipca_idx = get_bcb_history(432, months_14)
if not ipca_idx.empty:
    idx_12m = ipca_idx.index[ipca_idx.index >= pd.to_datetime(months_12)]
    if not idx_12m.empty:
        start_val = ipca_idx.loc[idx_12m[0]]
        end_val = ipca_idx.iloc[-1]
        print(f"\nIPCA Index (432) 12m variation: {((end_val/start_val)-1)*100:.2f}%")
