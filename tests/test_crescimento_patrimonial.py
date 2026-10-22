import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from views.crescimento_patrimonial import compute_patrimonio_growth
import db.crescimento as db_crescimento


def test_compute_patrimonio_growth_empty():
    empty_df = pd.DataFrame()
    result = compute_patrimonio_growth(empty_df)
    assert result.empty
    assert list(result.columns) == ['id', 'ano', 'valor_final', 'crescimento_pct', 'variacao_brl']


def test_compute_patrimonio_growth_single_year():
    df = pd.DataFrame([
        {'id': 1, 'ano': 2023, 'valor_final': 100000.0}
    ])
    result = compute_patrimonio_growth(df)
    assert len(result) == 1
    assert result.iloc[0]['ano'] == 2023
    assert result.iloc[0]['valor_final'] == 100000.0
    assert result.iloc[0]['crescimento_pct'] is None
    assert pd.isna(result.iloc[0]['variacao_brl'])


def test_compute_patrimonio_growth_multiple_years_ordering():
    # Envia os anos fora de ordem
    df = pd.DataFrame([
        {'id': 1, 'ano': 2021, 'valor_final': 50000.0},
        {'id': 3, 'ano': 2023, 'valor_final': 150000.0},
        {'id': 2, 'ano': 2022, 'valor_final': 100000.0},
    ])
    result = compute_patrimonio_growth(df)
    
    # A ordenação final na tabela DEVE ser o ano mais recente primeiro (ano DESC)
    assert list(result['ano']) == [2023, 2022, 2021]
    
    # Validação dos cálculos
    # 2023 em relação a 2022: (150000 - 100000) / 100000 = +50%
    row_2023 = result[result['ano'] == 2023].iloc[0]
    assert row_2023['variacao_brl'] == 50000.0
    assert pytest.approx(row_2023['crescimento_pct'], 0.01) == 50.0

    # 2022 em relação a 2021: (100000 - 50000) / 50000 = +100%
    row_2022 = result[result['ano'] == 2022].iloc[0]
    assert row_2022['variacao_brl'] == 50000.0
    assert pytest.approx(row_2022['crescimento_pct'], 0.01) == 100.0

    # 2021 é o ano base
    row_2021 = result[result['ano'] == 2021].iloc[0]
    assert pd.isna(row_2021['crescimento_pct'])
    assert pd.isna(row_2021['variacao_brl'])


def test_compute_patrimonio_growth_negative():
    df = pd.DataFrame([
        {'id': 1, 'ano': 2023, 'valor_final': 100000.0},
        {'id': 2, 'ano': 2024, 'valor_final': 80000.0},
    ])
    result = compute_patrimonio_growth(df)
    row_2024 = result[result['ano'] == 2024].iloc[0]
    
    assert row_2024['variacao_brl'] == -20000.0
    assert pytest.approx(row_2024['crescimento_pct'], 0.01) == -20.0


def test_db_save_crescimento_patrimonial():
    with patch('db.crescimento.get_db_connection') as mock_conn:
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_connection
        
        db_crescimento.save_crescimento_patrimonial(2025, 250000.0, 10)
        
        assert mock_cursor.execute.called
        query_executed = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]
        assert "INSERT INTO crescimento_patrimonial" in query_executed
        assert params == (10, 2025, 250000.0)
        assert mock_connection.commit.called


def test_db_update_crescimento_patrimonial():
    with patch('db.crescimento.get_db_connection') as mock_conn:
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_connection
        
        db_crescimento.update_crescimento_patrimonial(5, 2024, 300000.0, 10)
        
        assert mock_cursor.execute.called
        query_executed = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]
        assert "UPDATE crescimento_patrimonial" in query_executed
        assert params == (2024, 300000.0, 5, 10)
        assert mock_connection.commit.called


def test_db_delete_crescimento_patrimonial():
    with patch('db.crescimento.get_db_connection') as mock_conn:
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_connection
        
        db_crescimento.delete_crescimento_patrimonial(7, 10)
        
        assert mock_cursor.execute.called
        query_executed = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]
        assert "DELETE FROM crescimento_patrimonial" in query_executed
        assert params == (7, 10)
        assert mock_connection.commit.called


def test_db_get_crescimento_record_by_year():
    with patch('db.crescimento.get_db_connection') as mock_conn:
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'id': 1, 'user_id': 10, 'ano': 2025, 'valor_final': 500000.0}
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_connection
        
        res = db_crescimento.get_crescimento_record_by_year(2025, 10)
        assert res is not None
        assert res['ano'] == 2025
        assert res['valor_final'] == 500000.0


def test_sync_crescimento_patrimonial_current_year():
    with patch('db.crescimento.save_crescimento_patrimonial') as mock_save:
        res = db_crescimento.sync_crescimento_patrimonial_current_year(10, 750000.0)
        assert res is True
        assert mock_save.called
        call_args = mock_save.call_args[0]
        # ano deve ser int, valor_final 750000.0, user_id 10
        assert isinstance(call_args[0], int)
        assert call_args[1] == 750000.0
        assert call_args[2] == 10


def test_check_and_rollover_crescimento_all_users():
    mock_users = [{'id': 1, 'username': 'user1'}, {'id': 2, 'username': 'user2'}]
    with patch('db.auth.get_all_users', return_value=mock_users), \
         patch('executive_report_service.get_user_portfolio_data', return_value=(None, None, None, 123450.0, None, None, None)), \
         patch('db.crescimento.save_crescimento_patrimonial') as mock_save, \
         patch('db.crescimento.clear_db_cache') as mock_cache:
        
        count = db_crescimento.check_and_rollover_crescimento_all_users()
        assert count == 2
        assert mock_save.call_count == 2
        assert mock_cache.called


def test_crescimento_patrimonial_table_styler():
    df = pd.DataFrame([
        {'id': 1, 'ano': 2024, 'valor_final': 80000.0},
        {'id': 2, 'ano': 2025, 'valor_final': 100000.0},
    ])
    df_growth = compute_patrimonio_growth(df)
    display_df = df_growth.copy()
    display_df['Ano'] = display_df['ano'].astype(str)
    display_df['Valor Final'] = display_df['valor_final'].apply(lambda v: f"R$ {v:,.2f}")
    display_df['Crescimento (%)'] = display_df['crescimento_pct'].apply(lambda v: f"{v:,.2f}%" if pd.notna(v) else "—")
    display_df['Variação (R$)'] = display_df['variacao_brl'].apply(lambda v: f"R$ {v:,.2f}" if pd.notna(v) else "—")

    cols_show = ['id', 'Ano', 'Valor Final', 'Crescimento (%)', 'Variação (R$)', 'crescimento_pct']
    table_df = display_df[cols_show].copy()

    def style_growth(row):
        pct_raw = row.get('crescimento_pct')
        color = ''
        if pd.notna(pct_raw) and pct_raw is not None:
            color = "color: #00CC96; font-weight: bold;" if pct_raw >= 0 else "color: #EF553B; font-weight: bold;"
        target_cols = ['Crescimento (%)', 'Variação (R$)']
        return [color if col in target_cols else '' for col in row.index]

    styled_table = table_df.style \
        .apply(style_growth, axis=1) \
        .set_properties(**{'text-align': 'center'}, subset=['Ano']) \
        .set_properties(**{'text-align': 'right'}, subset=['Valor Final', 'Crescimento (%)', 'Variação (R$)'])

    # Computing the styler must succeed without ValueError
    res = styled_table._compute()
    assert res is not None

