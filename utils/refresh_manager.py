import holidays
from datetime import datetime
from zoneinfo import ZoneInfo

def is_market_open(market_type):
    """
    Verifica se o mercado especificado está aberto no momento atual.
    
    Regras:
    - BR: Ações e Fiis. 09:00 às 19:00, dias úteis, excluindo feriados em SP.
    - US: Stocks e Reits. 11:00 às 19:00, dias úteis, excluindo feriados em NY.
    - CRYPTO: Sempre True (24/7).
    """
    if market_type == 'CRYPTO':
        return True
    
    if market_type == 'BR':
        tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(tz)
        
        # Dias úteis (Segunda=0, Sexta=4)
        if now.weekday() > 4:
            return False
            
        # Horário: 09:00 às 19:00
        if not (9 <= now.hour < 19):
            return False
            
        # Feriados em SP
        br_holidays = holidays.BR(state='SP')
        if now.date() in br_holidays:
            return False
            
        return True

    if market_type == 'US':
        tz = ZoneInfo("America/New_York")
        now = datetime.now(tz)
        
        # Dias úteis
        if now.weekday() > 4:
            return False
            
        # Horário: 11:00 às 19:00 (Conforme solicitado pelo usuário)
        if not (11 <= now.hour < 19):
            return False
            
        # Feriados em NY
        us_holidays = holidays.US(state='NY')
        if now.date() in us_holidays:
            return False
            
        return True

    return True # Default safe fallback

def get_market_status():
    """Retorna um dicionário com o status de cada mercado."""
    return {
        'BR': is_market_open('BR'),
        'US': is_market_open('US'),
        'CRYPTO': True
    }
