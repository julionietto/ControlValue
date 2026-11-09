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


def test_empty_unified_df_columns():
    import pandas as pd
    from utils.formatters import format_ticker_for_display
    
    all_rows = []
    cols = [
        'id', 'ticker', 'Tipo', 'Quantidade', 'Preço', 'Valor da operação',
        'Cotação Atual', 'Valor atualizado', 'Orientação', 'Lucro / Prejuízo',
        'Peso %', 'currency'
    ]
    unified_df = pd.DataFrame(all_rows, columns=cols)
    assert not unified_df.columns.empty
    assert 'ticker' in unified_df.columns

    display_unified = unified_df.copy()
    display_unified['ticker'] = display_unified['ticker'].apply(format_ticker_for_display)
    assert 'ticker' in display_unified.columns
    assert len(display_unified) == 0


def test_radar_winner_and_priority_comparison():
    import pandas as pd
    from views.geral import get_target_class_key_for_asset, compute_radar_winner, compare_radar_priorities

    # Test get_target_class_key_for_asset mapping
    assert get_target_class_key_for_asset({'asset_type': 'Ações', 'ticker': 'PETR4.SA'}) == 'Ações'
    assert get_target_class_key_for_asset({'asset_type': 'ETF', 'ticker': 'HASH11.SA'}) == 'Criptos'
    assert get_target_class_key_for_asset({'asset_type': 'ETF', 'ticker': 'BOVA11.SA'}) == 'Ações'
    assert get_target_class_key_for_asset({'asset_type': 'Fiis', 'ticker': 'HGLG11.SA'}) == 'Fiis'
    assert get_target_class_key_for_asset({'asset_type': 'Renda Fixa', 'ticker': 'TESOURO SELIC'}) == 'Renda Fixa'
    assert get_target_class_key_for_asset({'asset_type': 'Stocks', 'ticker': 'AAPL'}) == 'Ativos Internacionais'
    assert get_target_class_key_for_asset({'asset_type': 'Reits', 'ticker': 'O'}) == 'Ativos Internacionais'

    # Setup mock portfolio
    df = pd.DataFrame([
        {
            'ticker': 'BBAS3.SA',
            'asset_type': 'Ações',
            'quantity': 100.0,
            'current_value': 2500.0,
            'original_current_price': 25.0,
            'price_ceiling': 30.0
        },
        {
            'ticker': 'VALE3.SA',
            'asset_type': 'Ações',
            'quantity': 100.0,
            'current_value': 6000.0,
            'original_current_price': 60.0,
            'price_ceiling': 70.0
        },
        {
            'ticker': 'AAPL',
            'asset_type': 'Stocks',
            'quantity': 10.0,
            'current_value': 5000.0,
            'original_current_price': 180.0,
            'price_ceiling': 200.0
        },
        {
            'ticker': 'O',
            'asset_type': 'Reits',
            'quantity': 20.0,
            'current_value': 3000.0,
            'original_current_price': 55.0,
            'price_ceiling': 60.0
        }
    ])

    user_targets = {
        'Ações': 40.0,
        'Fiis': 20.0,
        'Criptos': 5.0,
        'Renda Fixa': 15.0,
        'Ativos Internacionais': 20.0
    }
    # Case 1: Ações has a 10% deficit (R$ 10.000), Ativos Internacionais has a 5% deficit (R$ 5.000)
    current_allocs_pct = {
        'Ações': 30.0,
        'Fiis': 25.0,
        'Criptos': 5.0,
        'Renda Fixa': 25.0,
        'Ativos Internacionais': 15.0
    }
    total_val = 100000.0

    br_winner = compute_radar_winner(df, ['Ações', 'ETF', 'Fiis', 'Renda Fixa', 'Fundo CETIP'], user_targets, current_allocs_pct, total_val)
    us_winner = compute_radar_winner(df, ['Stocks', 'Reits'], user_targets, current_allocs_pct, total_val)

    assert br_winner is not None
    assert br_winner['ticker'] == 'BBAS3'
    assert br_winner['deficit_pct'] == 10.0
    assert br_winner['deficit_brl'] == 10000.0

    assert us_winner is not None
    assert us_winner['ticker'] == 'O'  # smaller current_value than AAPL
    assert us_winner['deficit_pct'] == 5.0
    assert us_winner['deficit_brl'] == 5000.0

    priority_region, details = compare_radar_priorities(br_winner, us_winner)
    assert priority_region == 'BR'
    assert details['primary']['ticker'] == 'BBAS3'
    assert details['secondary']['ticker'] == 'O'

    # Case 2: Ativos Internacionais has a larger deficit (12% = R$ 12.000) than Ações (5% = R$ 5.000)
    current_allocs_pct_2 = {
        'Ações': 35.0,
        'Fiis': 25.0,
        'Criptos': 5.0,
        'Renda Fixa': 27.0,
        'Ativos Internacionais': 8.0
    }
    br_winner_2 = compute_radar_winner(df, ['Ações', 'ETF', 'Fiis', 'Renda Fixa', 'Fundo CETIP'], user_targets, current_allocs_pct_2, total_val)
    us_winner_2 = compute_radar_winner(df, ['Stocks', 'Reits'], user_targets, current_allocs_pct_2, total_val)

    priority_region_2, details_2 = compare_radar_priorities(br_winner_2, us_winner_2)
    assert priority_region_2 == 'US'
    assert details_2['primary']['ticker'] == 'O'
    assert details_2['secondary']['ticker'] == 'BBAS3'



