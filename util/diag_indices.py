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
        # Normaliza para comparação
        start_dt = pd.to_datetime(start_date).normalize()
        df = df[df['data'] >= start_dt]
        return df.set_index('data')['valor']
    return pd.Series()

# Setup dates
hoje = pd.Timestamp.now().normalize()
months_13 = (hoje - pd.DateOffset(months=13)).normalize()

print(f"Hoje: {hoje}")
print(f"Start 13m: {months_13}")

# 1. IPCA Index (432)
ipca_idx = get_bcb_history(432, months_13 - pd.Timedelta(days=31))
if not ipca_idx.empty:
    # Simula meses fechamento (fim de mês)
    meses = []
    for i in range(13, -1, -1):
        meses.append((hoje - pd.DateOffset(months=i) + pd.offsets.MonthEnd(0)).normalize())
    
    # Reindex and ffill
    full = pd.date_range(start=ipca_idx.index.min(), end=meses[-1], freq='D')
    ipca_daily = ipca_idx.reindex(full).ffill().bfill()
    ipca_resampled = ipca_daily.reindex(meses).ffill().bfill()
    
    total_ipca = (ipca_resampled.iloc[-1] / ipca_resampled.iloc[0] - 1) * 100
    print(f"\nIPCA (432) 12m accumulated (13 points): {total_ipca:.2f}%")
    print(f"First date: {ipca_resampled.index[0]}, Last date: {ipca_resampled.index[-1]}")

# 2. CDI (4391)
cdi = get_bcb_history(4391, months_13 - pd.Timedelta(days=31))
if not cdi.empty:
    cdi_cum = (1 + cdi/100).cumprod()
    full = pd.date_range(start=cdi_cum.index.min(), end=meses[-1], freq='D')
    cdi_daily = cdi_cum.reindex(full).ffill().bfill()
    cdi_resampled = cdi_daily.reindex(meses).ffill().bfill()
    
    total_cdi = (cdi_resampled.iloc[-1] / cdi_resampled.iloc[0] - 1) * 100
    print(f"CDI (4391) 12m accumulated (13 points): {total_cdi:.2f}%")

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
