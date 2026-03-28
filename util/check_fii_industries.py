import yfinance as yf
import database as db

def check_fii_industries():
    df = db.get_all_assets()
    fii_df = df[df['asset_type'] == 'Fiis']
    
    print(f"{'Ticker':<10} | {'Industry':<30}")
    print("-" * 45)
    
    for ticker in fii_df['ticker']:
        try:
            info = yf.Ticker(ticker).info
            industry = info.get('industry', 'N/A')
            print(f"{ticker:<10} | {industry:<30}")
        except Exception as e:
            print(f"{ticker:<10} | Error: {e}")

if __name__ == "__main__":
    check_fii_industries()
