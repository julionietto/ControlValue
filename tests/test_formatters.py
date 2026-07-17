import pytest
from utils.formatters import format_ticker_for_display, escape_html, format_brl, infer_asset_type

def test_format_ticker_for_display():
    assert format_ticker_for_display("PETR4.SA") == "PETR4"
    assert format_ticker_for_display("AAPL") == "AAPL"
    assert format_ticker_for_display(None) is None
    assert format_ticker_for_display(123) == 123

def test_escape_html():
    assert escape_html("hello") == "hello"
    assert escape_html("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert escape_html(None) == ""

def test_format_brl():
    assert format_brl(100.0) == "R$ 100,00"
    assert format_brl(1234.56) == "R$ 1.234,56"
    assert format_brl(0.0) == "R$ 0,00"
    assert format_brl(-50.5) == "R$ -50,50"
    assert format_brl("invalid") == "invalid"

def test_infer_asset_type_crypto():
    assert infer_asset_type("BTC-USD") == "Cripto"
    assert infer_asset_type("BTC") == "Cripto"
    assert infer_asset_type("ETH") == "Cripto"

def test_infer_asset_type_reits():
    assert infer_asset_type("AAPL") == "Reits"
    assert infer_asset_type("MSFT") == "Reits"

def test_infer_asset_type_crypto_etf():
    assert infer_asset_type("HASH11.SA") == "ETF"
    assert infer_asset_type("HASH11") == "ETF"
    assert infer_asset_type("QBTC11.SA") == "ETF"

def test_infer_asset_type_fii_fallback():
    # Se falhar no yfinance, deve retornar Fiis pelo sufixo 11.SA
    assert infer_asset_type("INVALID11.SA") == "Fiis"

def test_infer_asset_type_fii_keywords(monkeypatch):
    class MockTicker:
        def __init__(self, ticker):
            pass
        @property
        def info(self):
            return {
                "sector": None,
                "industry": None,
                "longName": "Fundo Investimento Imobiliario Iridium Recebiveis Imobiliarios"
            }
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", MockTicker)
    assert infer_asset_type("IRDM11.SA") == "Fiis"

def test_get_annual_proventos_summary():
    import pandas as pd
    import datetime
    from utils.formatters import get_annual_proventos_summary

    current_date = datetime.date.today()
    current_year = current_date.year
    current_month = current_date.month

    data = [
        # Past year (always divided by 12)
        {"ticker": "PETR4", "ano": current_year - 1, "mes": 1, "valor": 120.0},
        # Current year (divided by current_month)
        {"ticker": "PETR4", "ano": current_year, "mes": 1, "valor": 120.0 * current_month},
    ]
    if current_month < 12:
        # Add a dividend in a future month of the current year (should not affect Valor Mensal)
        data.append({"ticker": "PETR4", "ano": current_year, "mes": current_month + 1, "valor": 500.0})

    df = pd.DataFrame(data)

    resumo = get_annual_proventos_summary(df, [current_year - 1, current_year])

    # Assert past year values
    row_past = resumo[resumo["Ano"] == str(current_year - 1)].iloc[0]
    assert row_past["Valor Anual"] == 120.0
    assert row_past["Valor Mensal"] == 10.0  # 120 / 12

    # Assert current year values
    row_current = resumo[resumo["Ano"] == str(current_year)].iloc[0]
    expected_anual = 120.0 * current_month
    if current_month < 12:
        expected_anual += 500.0
    assert row_current["Valor Anual"] == expected_anual
    assert row_current["Valor Mensal"] == 120.0  # (120 * current_month) / current_month

