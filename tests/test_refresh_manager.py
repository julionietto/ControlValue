import pytest
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo
from utils.refresh_manager import is_market_open, get_market_status

# Usaremos um patch para datetime no módulo utils.refresh_manager
@patch('utils.refresh_manager.datetime')
def test_is_market_open_br_weekend(mock_datetime):
    # Simula um sábado às 14:00 (dia 23/05/2026 é sábado)
    mock_datetime.now.return_value = datetime(2026, 5, 23, 14, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
    
    assert is_market_open('BR') is False

@patch('utils.refresh_manager.datetime')
def test_is_market_open_br_business_day_open(mock_datetime):
    # Simula uma segunda-feira às 14:00 (dia 25/05/2026 é segunda)
    mock_datetime.now.return_value = datetime(2026, 5, 25, 14, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
    
    assert is_market_open('BR') is True

@patch('utils.refresh_manager.datetime')
def test_is_market_open_br_business_day_closed_early(mock_datetime):
    # Simula uma segunda-feira às 08:00 (dia 25/05/2026 é segunda)
    mock_datetime.now.return_value = datetime(2026, 5, 25, 8, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
    
    assert is_market_open('BR') is False

@patch('utils.refresh_manager.datetime')
def test_is_market_open_br_business_day_closed_late(mock_datetime):
    # Simula uma segunda-feira às 20:00 (dia 25/05/2026 é segunda)
    mock_datetime.now.return_value = datetime(2026, 5, 25, 20, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
    
    assert is_market_open('BR') is False

@patch('utils.refresh_manager.datetime')
def test_is_market_open_us_business_day_open(mock_datetime):
    # Simula uma quarta-feira às 14:00 em NY (dia 20/05/2026 - sem feriados)
    mock_datetime.now.return_value = datetime(2026, 5, 20, 14, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
    
    assert is_market_open('US') is True

@patch('utils.refresh_manager.datetime')
def test_is_market_open_us_business_day_closed_early(mock_datetime):
    # Simula uma segunda-feira às 09:00 em NY (dia 25/05/2026)
    mock_datetime.now.return_value = datetime(2026, 5, 25, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
    
    assert is_market_open('US') is False


def test_get_logical_sync_date_midnight_rollover():
    from sync_job import get_logical_sync_date
    sp_tz = ZoneInfo("America/Sao_Paulo")

    # Execução normal à noite (18:23 BRT ou 23:40 BRT do dia 16/11) -> ciclo 2026-11-16
    assert get_logical_sync_date(datetime(2026, 11, 16, 18, 23, 0, tzinfo=sp_tz)) == "2026-11-16"
    assert get_logical_sync_date(datetime(2026, 11, 16, 23, 40, 0, tzinfo=sp_tz)) == "2026-11-16"

    # Execução atrasada pela fila do GitHub Actions após a meia-noite (00:19 BRT do dia 17/11) -> ainda pertence ao ciclo 2026-11-16
    assert get_logical_sync_date(datetime(2026, 11, 17, 0, 19, 0, tzinfo=sp_tz)) == "2026-11-16"
    assert get_logical_sync_date(datetime(2026, 11, 17, 5, 59, 59, tzinfo=sp_tz)) == "2026-11-16"

    # Execução a partir das 06:00 BRT do dia 17/11 -> pertence ao ciclo 2026-11-17
    assert get_logical_sync_date(datetime(2026, 11, 17, 6, 0, 0, tzinfo=sp_tz)) == "2026-11-17"
    assert get_logical_sync_date(datetime(2026, 11, 17, 23, 40, 11, tzinfo=sp_tz)) == "2026-11-17"

