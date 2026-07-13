import yfinance as yf
ticker = "IRDM11.SA"
info = yf.Ticker(ticker).info
print("SECTOR:", info.get('sector'))
print("INDUSTRY:", info.get('industry'))
print("LONG NAME:", info.get('longName'))
