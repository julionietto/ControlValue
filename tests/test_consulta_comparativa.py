import pandas as pd
import pytest
from views.proventos_historico import obter_dados_consulta_comparativa

def test_obter_dados_consulta_comparativa_ordem_alfabetica():
    # Dados fictícios desordenados
    data = [
        {'ano': 2024, 'mes': 5, 'ticker': 'VALE3.SA', 'valor': 100.0},
        {'ano': 2024, 'mes': 5, 'ticker': 'BBAS3.SA', 'valor': 50.0},
        {'ano': 2024, 'mes': 5, 'ticker': 'ITSA4.SA', 'valor': 25.0},
        {'ano': 2023, 'mes': 5, 'ticker': 'VALE3.SA', 'valor': 80.0},
        {'ano': 2023, 'mes': 5, 'ticker': 'PETR4.SA', 'valor': 200.0},
    ]
    df = pd.DataFrame(data)

    rows, total_a, total_b, total_diff = obter_dados_consulta_comparativa(df, 2024, 5, 2023, 5)

    # Ativos com proventos em 2024-05 ou 2023-05: BBAS3, ITSA4, PETR4, VALE3 (formatados sem .SA)
    tickers_result = [r['display_ticker'] for r in rows]
    assert tickers_result == ['BBAS3', 'ITSA4', 'PETR4', 'VALE3'], f"Esperado ordem alfabética, obteve {tickers_result}"

    assert total_a == 175.0  # 100 + 50 + 25
    assert total_b == 280.0  # 80 + 200
    assert total_diff == 175.0 - 280.0

def test_obter_dados_consulta_comparativa_apenas_um_lado():
    data = [
        {'ano': 2024, 'mes': 1, 'ticker': 'MXRF11.SA', 'valor': 15.0},
        {'ano': 2024, 'mes': 1, 'ticker': 'HGLG11.SA', 'valor': 30.0},
    ]
    df = pd.DataFrame(data)

    rows, total_a, total_b, total_diff = obter_dados_consulta_comparativa(df, 2024, 1, 2023, 1)
    
    assert len(rows) == 2
    assert rows[0]['display_ticker'] == 'HGLG11'
    assert rows[0]['valor_a'] == 30.0
    assert rows[0]['valor_b'] == 0.0
    
    assert rows[1]['display_ticker'] == 'MXRF11'
    assert rows[1]['valor_a'] == 15.0
    assert rows[1]['valor_b'] == 0.0

def test_obter_dados_consulta_comparativa_vazio():
    df = pd.DataFrame(columns=['ano', 'mes', 'ticker', 'valor'])
    rows, total_a, total_b, total_diff = obter_dados_consulta_comparativa(df, 2024, 1, 2023, 1)
    assert rows == []
    assert total_a == 0.0
    assert total_b == 0.0
    assert total_diff == 0.0
