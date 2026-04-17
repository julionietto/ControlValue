import holidays
from datetime import datetime
from zoneinfo import ZoneInfo

def is_market_open(market_type):
    """
    Verifica se o mercado especificado está aberto no momento atual.
    
    Regras:
    - BR: Ações e Fiis. 10:00 às 18:30, dias úteis, excluindo feriados em SP.
    - US: Stocks e Reits. 11:00 às 18:30, dias úteis, excluindo feriados em NY.
    - CRYPTO: Agora obedece às regras dos demais mercados (não força refresh sozinho).
    """
    if market_type == 'CRYPTO':
        return False # Não força o auto-refresh sozinho
    
    if market_type == 'BR':
        tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(tz)
        
        # Dias úteis (Segunda=0, Sexta=4)
        if now.weekday() > 4:
            return False
            
        # Horário: 10:00 às 18:30
        open_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
        close_time = now.replace(hour=18, minute=30, second=0, microsecond=0)
        
        if not (open_time <= now <= close_time):
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
            
        # Horário: 11:00 às 18:30
        open_time = now.replace(hour=11, minute=0, second=0, microsecond=0)
        close_time = now.replace(hour=18, minute=30, second=0, microsecond=0)
        
        if not (open_time <= now <= close_time):
            return False
            
        # Feriados em NY
        us_holidays = holidays.US(state='NY')
        if now.date() in us_holidays:
            return False
            
        return True

    return False # Default safe fallback

def get_market_status():
    """Retorna um dicionário com o status de cada mercado."""
    return {
        'BR': is_market_open('BR'),
        'US': is_market_open('US')
    }
