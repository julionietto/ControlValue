import pytest
import pandas as pd
from services import _normalize_ticker_for_yf, fetch_current_prices

def test_normalize_ticker_for_yf():
    yf_t, aliases = _normalize_ticker_for_yf("MGLU3")
    assert yf_t == "MGLU3.SA"
    assert "MGLU3" in aliases
    assert "MGLU3.SA" in aliases

    yf_t_sa, aliases_sa = _normalize_ticker_for_yf("PETR4.SA")
    assert yf_t_sa == "PETR4.SA"
    assert "PETR4" in aliases_sa
    assert "PETR4.SA" in aliases_sa

    yf_t_crypto, aliases_crypto = _normalize_ticker_for_yf("BTC")
    assert yf_t_crypto == "BTC-USD"
    assert "BTC" in aliases_crypto
    assert "BTC-USD" in aliases_crypto

    yf_t_us, aliases_us = _normalize_ticker_for_yf("AAPL")
    assert yf_t_us == "AAPL"
    assert "AAPL" in aliases_us

    yf_t_reit, aliases_reit = _normalize_ticker_for_yf("NHI")
    assert yf_t_reit == "NHI"
    assert "NHI" in aliases_reit

    yf_t_ind, aliases_ind = _normalize_ticker_for_yf("^BVSP")
    assert yf_t_ind == "^BVSP"
    assert "^BVSP" in aliases_ind


def test_fetch_current_prices_alias_mapping(monkeypatch):
    """Testa se fetch_current_prices mapeia os preços para ambas as versões do ticker (com e sem .SA)."""
    
    def mock_download(tickers, **kwargs):
        close_df = pd.DataFrame({'TESTM3.SA': [2.15]}, index=[pd.Timestamp('2026-09-01')])
        return pd.concat({'Close': close_df}, axis=1)

    monkeypatch.setattr("yfinance.download", mock_download)

    prices = fetch_current_prices(["TESTM3", "TESTM3.SA"], refresh_id=99999)
    assert "TESTM3" in prices
    assert "TESTM3.SA" in prices
    assert prices["TESTM3"] == 2.15
    assert prices["TESTM3.SA"] == 2.15
