import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock
from db.dividends import check_and_create_next_year_dashboard


def test_check_and_create_next_year_dashboard_not_december():
    # Quando o mês não for dezembro (ex: novembro), não deve fazer nada e retornar False
    fake_now = datetime(2026, 11, 20, 10, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    with patch("db.dividends.datetime") as mock_dt, \
         patch("db.dividends.get_db_connection") as mock_conn:
        mock_dt.now.return_value = fake_now
        
        result = check_and_create_next_year_dashboard(user_id=1)
        assert result is False
        mock_conn.assert_not_called()


def test_check_and_create_next_year_dashboard_already_exists():
    # Em dezembro, mas o próximo ano já possui registros na tabela proventos
    fake_now = datetime(2026, 12, 1, 9, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (99,)  # Já existe registro
    mock_connection = MagicMock()
    mock_connection.__enter__.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    with patch("db.dividends.datetime") as mock_dt, \
         patch("db.dividends.get_db_connection", return_value=mock_connection), \
         patch("db.dividends.clear_db_cache") as mock_clear:
        mock_dt.now.return_value = fake_now

        result = check_and_create_next_year_dashboard(user_id=1)
        assert result is False
        mock_connection.commit.assert_not_called()
        mock_clear.assert_not_called()


def test_check_and_create_next_year_dashboard_filtering_active_and_sold_assets():
    # Em dezembro, criando o ano seguinte:
    # 1. Ativos ativos em carteira (quantity > 0): 'BBAS3.SA' e 'AAPL'
    # 2. Ativo vendido com provento provisionado para o próximo ano: 'VALE3.SA'
    # 3. Ativo vendido SEM provento para o próximo ano (ex: 'PETR4.SA') não deve ser incluído
    fake_now = datetime(2026, 12, 5, 14, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    
    mock_cursor = MagicMock()
    # 1a chamada fetchone: SELECT id FROM proventos WHERE ano = next_year -> None (não existe)
    mock_cursor.fetchone.side_effect = [None]
    
    # fetchall side effects:
    # 1a: SELECT DISTINCT ticker FROM assets WHERE user_id = %s AND quantity > 0
    # 2a: SELECT DISTINCT COALESCE(a.ticker, p.ticker) FROM proventos_provisionados ...
    mock_cursor.fetchall.side_effect = [
        [('BBAS3.SA',), ('AAPL',)],       # Ativos em custódia com quantity > 0
        [('VALE3.SA',)],                  # Ativo vendido que tem provento provisionado no próximo ano
    ]
    
    mock_connection = MagicMock()
    mock_connection.__enter__.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    with patch("db.dividends.datetime") as mock_dt, \
         patch("db.dividends.get_db_connection", return_value=mock_connection), \
         patch("db.dividends.sync_proventos_from_provisionados") as mock_sync, \
         patch("db.dividends.clear_db_cache") as mock_clear:
        mock_dt.now.return_value = fake_now

        result = check_and_create_next_year_dashboard(user_id=1)
        assert result is True

        # Valida que inseriu para 2027 apenas os elegíveis: AAPL, BBAS3.SA e VALE3.SA
        insert_calls = [
            c for c in mock_cursor.execute.call_args_list
            if "INSERT INTO proventos" in c[0][0]
        ]
        inserted_tickers = [c[0][1][1] for c in insert_calls]
        assert sorted(inserted_tickers) == ['AAPL', 'BBAS3.SA', 'VALE3.SA']
        
        # Cada insert deve ter ano 2027, ticker elegivel, user_id 1
        for c in insert_calls:
            params = c[0][1]
            assert params[0] == 2027
            assert params[2] == 1

        mock_connection.commit.assert_called_once()
        mock_clear.assert_called_once()
        mock_sync.assert_called_once_with(1)


def test_check_and_create_next_year_dashboard_sold_without_proventos_excluded():
    # Cenário onde não há proventos provisionados futuros para ativos vendidos
    fake_now = datetime(2026, 12, 10, 8, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [None]
    mock_cursor.fetchall.side_effect = [
        [('ITUB4.SA',)],  # Apenas 1 ativo ativo em custódia
        [],               # Nenhum provento provisionado para o próximo ano
    ]
    
    mock_connection = MagicMock()
    mock_connection.__enter__.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    with patch("db.dividends.datetime") as mock_dt, \
         patch("db.dividends.get_db_connection", return_value=mock_connection), \
         patch("db.dividends.sync_proventos_from_provisionados") as mock_sync, \
         patch("db.dividends.clear_db_cache") as mock_clear:
        mock_dt.now.return_value = fake_now

        result = check_and_create_next_year_dashboard(user_id=42)
        assert result is True

        insert_calls = [
            c for c in mock_cursor.execute.call_args_list
            if "INSERT INTO proventos" in c[0][0]
        ]
        assert len(insert_calls) == 1
        assert insert_calls[0][0][1][1] == 'ITUB4.SA'
        assert insert_calls[0][0][1][2] == 42
