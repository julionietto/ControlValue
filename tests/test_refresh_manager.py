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
