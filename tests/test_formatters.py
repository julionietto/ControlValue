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
