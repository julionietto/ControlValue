import psycopg2.extras
from db.connection import get_db_connection
import pandas as pd

def recalculate_asset_balance(asset_id, conn):
    """Recalcula a quantidade e o preço médio de um ativo com base no histórico."""
    cursor = conn.cursor()
    cursor.execute("SELECT quantity, unit_price FROM asset_history WHERE asset_id = %s", (asset_id,))
    history = cursor.fetchall()
    
    total_quantity = 0.0
    total_cost = 0.0
    
    for qty, price in history:
        total_quantity += qty
        if qty > 0: # Compra: aumenta o custo total
            total_cost += qty * price
            
    cursor.execute("SELECT SUM(quantity), SUM(quantity * unit_price) FROM asset_history WHERE asset_id = %s AND quantity > 0", (asset_id,))
    total_buy_qty, total_buy_cost = cursor.fetchone()
    
    avg_price = total_buy_cost / total_buy_qty if total_buy_qty and total_buy_qty > 0 else 0.0
    
    cursor.execute("SELECT SUM(quantity) FROM asset_history WHERE asset_id = %s", (asset_id,))
    final_qty = cursor.fetchone()[0] or 0.0
    
    cursor.execute(
        "UPDATE assets SET quantity = %s, average_price = %s WHERE id = %s",
        (final_qty, avg_price, asset_id)
    )

def get_all_assets(user_id):
    """Retorna todos os ativos do usuário."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM assets WHERE user_id = %s ORDER BY ticker ASC", (user_id,))
        rows = cursor.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()

def add_empty_asset(ticker, asset_type, user_id, currency='BRL'):
    ticker = ticker.upper()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE ticker = %s AND user_id = %s", (ticker, user_id))
        existing_asset = cursor.fetchone()
        
        if not existing_asset:
            cursor.execute(
                "INSERT INTO assets (ticker, asset_type, quantity, average_price, user_id, currency) VALUES (%s, %s, 0, 0, %s, %s)",
                (ticker, asset_type, user_id, currency)
            )
            conn.commit()
            return True
        return False

def get_asset_by_id(asset_id, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM assets WHERE id = %s AND user_id = %s", (asset_id, user_id))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_asset_operation(asset_id, user_id, date, quantity, unit_price):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE id = %s AND user_id = %s", (asset_id, user_id))
        if cursor.fetchone():
            cursor.execute(
                "INSERT INTO asset_history (asset_id, date, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                (asset_id, date, quantity, unit_price)
            )
            recalculate_asset_balance(asset_id, conn)
            conn.commit()

def update_asset_operation(operation_id, asset_id, user_id, date, quantity, unit_price):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE id = %s AND user_id = %s", (asset_id, user_id))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE asset_history SET date = %s, quantity = %s, unit_price = %s WHERE id = %s AND asset_id = %s",
                (date, quantity, unit_price, operation_id, asset_id)
            )
            recalculate_asset_balance(asset_id, conn)
            conn.commit()

def delete_asset_operation(operation_id, asset_id, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE id = %s AND user_id = %s", (asset_id, user_id))
        if cursor.fetchone():
            cursor.execute("DELETE FROM asset_history WHERE id = %s AND asset_id = %s", (operation_id, asset_id))
            recalculate_asset_balance(asset_id, conn)
            conn.commit()

def delete_asset(asset_id, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM asset_history WHERE asset_id = %s", (asset_id,))
        cursor.execute("DELETE FROM assets WHERE id = %s AND user_id = %s", (asset_id, user_id))
        conn.commit()

def get_asset_history(asset_id, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT id, date, quantity, unit_price FROM asset_history WHERE asset_id = %s ORDER BY date ASC", (asset_id,))
        rows = cursor.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()

def get_all_asset_histories(user_id):
    """Busca o histórico de operações de TODOS os ativos do usuário em um único Round-Trip."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        query = '''
            SELECT h.* FROM asset_history h 
            JOIN assets a ON h.asset_id = a.id 
            WHERE a.user_id = %s 
            ORDER BY h.date ASC
        '''
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()

def add_or_update_fixed_income_asset(ticker, saldo, user_id, asset_type='Renda Fixa'):
    ticker = ticker.upper()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE ticker = %s AND user_id = %s", (ticker, user_id))
        existing_asset = cursor.fetchone()
        
        if existing_asset:
            asset_id = existing_asset[0]
            cursor.execute(
                "UPDATE assets SET quantity = 1, average_price = %s, asset_type = %s WHERE id = %s AND user_id = %s",
                (saldo, asset_type, asset_id, user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO assets (ticker, asset_type, quantity, average_price, user_id) VALUES (%s, %s, 1, %s, %s)",
                (ticker, asset_type, saldo, user_id)
            )
        conn.commit()

def update_asset_valuation(asset_id, user_id, price_ceiling, fair_value):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE assets SET price_ceiling = %s, fair_value = %s WHERE id = %s AND user_id = %s",
            (price_ceiling, fair_value, asset_id, user_id)
        )
        conn.commit()

def get_user_allocations(user_id):
    """Retorna as metas de alocação de classes de ativos do usuário."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT asset_class, allocation_percent FROM user_allocations WHERE user_id = %s", (user_id,))
        rows = cursor.fetchall()
        
    if not rows:
        return {
            'Ações': 20.0, 'Fiis': 20.0, 'Ativos Internacionais': 20.0,
            'Criptos': 20.0, 'Renda Fixa': 20.0
        }

    allocations = {
        'Ações': 0.0, 'Fiis': 0.0, 'Ativos Internacionais': 0.0,
        'Criptos': 0.0, 'Renda Fixa': 0.0
    }
    for row in rows:
        if row[0] in allocations:
            allocations[row[0]] = float(row[1])
    return allocations

def save_user_allocations(user_id, allocations_dict):
    """Salva ou atualiza as metas de alocação de classes de ativos do usuário."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for asset_class, percent in allocations_dict.items():
            cursor.execute("""
                INSERT INTO user_allocations (user_id, asset_class, allocation_percent)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, asset_class) 
                DO UPDATE SET allocation_percent = EXCLUDED.allocation_percent
            """, (user_id, asset_class, percent))
        conn.commit()

CRYPTO_ETFS = {
    # B3 Crypto ETFs
    'HASH11.SA', 'QBTC11.SA', 'QETH11.SA', 'BITH11.SA', 'ETHE11.SA', 
    'DEFI11.SA', 'WEB311.SA', 'NFTS11.SA', 'CRPT11.SA', 'META11.SA',
    'HASH11', 'QBTC11', 'QETH11', 'BITH11', 'ETHE11', 
    'DEFI11', 'WEB311', 'NFTS11', 'CRPT11', 'META11',
    # US Crypto ETFs
    'IBIT', 'FBTC', 'ARKB', 'BITB', 'GBTC', 'BTCO', 
    'EZBC', 'BRRR', 'HODL', 'BTCW'
}

def infer_asset_type(ticker):
    """Infere o tipo de ativo (Ações, FIIs, etc) com base no ticker."""
    ticker = ticker.upper()
    if ticker in CRYPTO_ETFS:
        return 'ETF'
    if ticker.endswith('.SA'):
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            sector = info.get('sector', '')
            industry = info.get('industry', '')
            long_name_raw = info.get('longName')
            long_name = str(long_name_raw).upper() if long_name_raw else ""
            if sector == 'Real Estate' and 'REIT' in str(industry): return 'Fiis'
            fii_keywords = [' FII', 'FII ', 'FUNDO DE INVESTIMENTO IMOBILI', 'FUNDO INVESTIMENTO IMOBILI', 'CREDITO IMOBILIARIO', 'FIAGRO', 'FUNDO DE INVEST IMOB', 'IMOBIL']
            if any(k in long_name for k in fii_keywords): return 'Fiis'
            etf_keywords = ['ETF', 'FUNDO DE INDICE', 'INDEX FUND', 'ISHARES']
            if any(k in long_name for k in etf_keywords): return 'ETF'
            if not sector and not industry:
                if not long_name:
                    if '11.SA' in ticker or ticker.endswith('11'): return 'Fiis'
                    return 'Ações'
                return 'ETF'
            return 'Ações'
        except Exception:
            if '11.SA' in ticker: return 'Fiis'
            return 'Ações'
    elif '-' in ticker or ticker in ['BTC', 'ETH', 'SOL', 'USDT', 'USDC']:
        return 'Cripto'
    else:
        return 'Reits'

def update_asset(asset_id, user_id, ticker, asset_type, quantity, average_price, price_ceiling=0, fair_value=0, currency='BRL'):
    ticker = ticker.upper()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if asset_type in ['Renda Fixa', 'Fundo CETIP']:
            cursor.execute(
                "UPDATE assets SET ticker = %s, asset_type = %s, quantity = %s, average_price = %s, price_ceiling = %s, fair_value = %s, currency = %s WHERE id = %s AND user_id = %s",
                (ticker, asset_type, quantity, average_price, price_ceiling, fair_value, currency, asset_id, user_id)
            )
        else:
            cursor.execute(
                "UPDATE assets SET ticker = %s, asset_type = %s, price_ceiling = %s, fair_value = %s, currency = %s WHERE id = %s AND user_id = %s",
                (ticker, asset_type, price_ceiling, fair_value, currency, asset_id, user_id)
            )
        conn.commit()

def import_assets_csv(file_content, user_id):
    import csv
    import io
    try:
        if hasattr(file_content, 'read'): f = io.StringIO(file_content.read().decode('utf-8'))
        else: f = io.StringIO(file_content)
        reader = csv.reader(f, delimiter=',')
        header = next(reader)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for row in reader:
                if not row or len(row) < 3: continue
                ticker = row[0].strip().upper()
                asset_type = row[1].strip()
                quantity = float(row[2].replace(',', '.'))
                avg_price = float(row[3].replace(',', '.'))
                cursor.execute("SELECT id FROM assets WHERE ticker = %s AND user_id = %s", (ticker, user_id))
                res = cursor.fetchone()
                if res:
                    cursor.execute("UPDATE assets SET quantity = %s, average_price = %s WHERE id = %s", (quantity, avg_price, res[0]))
                else:
                    cursor.execute("INSERT INTO assets (ticker, asset_type, quantity, average_price, user_id) VALUES (%s, %s, %s, %s, %s)", (ticker, asset_type, quantity, avg_price, user_id))
            conn.commit()
        return True, "Importação concluída."
    except Exception as e:
        return False, f"Erro: {e}"
