import sqlite3
import pandas as pd
import hashlib
import bcrypt
from contextlib import contextmanager

DB_NAME = "portfolio.db"

def hash_password(password):
    """Gera um hash bcrypt para a senha."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(plain_password, hashed_password):
    """
    Verifica se a senha coincide com o hash atual (bcrypt) ou legado (SHA-256).
    Retorna dois booleanos: (is_valid, needs_rehash).
    """
    plain_bytes = plain_password.encode()
    if hashed_password.startswith('$2b$'):
        # Hash novo (bcrypt)
        try:
            is_valid = bcrypt.checkpw(plain_bytes, hashed_password.encode())
            return is_valid, False
        except Exception:
            return False, False
    else:
        # Hash antigo (SHA-256)
        legacy_hash = hashlib.sha256(plain_bytes).hexdigest()
        if legacy_hash == hashed_password:
            return True, True  # A senha está correta, mas o hash está desatualizado
        return False, False

def infer_asset_type(ticker):
    ticker = ticker.upper()
    if ticker.endswith('.SA'):
        if '11.SA' in ticker:
            return 'Fiis'
        return 'Ações'
    elif '-' in ticker or ticker in ['BTC', 'ETH', 'SOL', 'USDT', 'USDC']:
        return 'Cripto'
    else:
        return 'Reits'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Tabela de Ativos (consolidado)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            quantity REAL NOT NULL,
            average_price REAL NOT NULL,
            price_ceiling REAL DEFAULT 0,
            fair_value REAL DEFAULT 0,
            user_id INTEGER NOT NULL DEFAULT 1
        )
    ''')
    # Tabela de Histórico de Operações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asset_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (asset_id) REFERENCES assets (id)
        )
    ''')
    # Tabela de Usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT,
            birth_date TEXT,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Tabela de Proventos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ano INTEGER NOT NULL,
            mes TEXT NOT NULL,
            ticker TEXT NOT NULL,
            valor REAL NOT NULL,
            user_id INTEGER NOT NULL DEFAULT 1
        )
    ''')
    # Tabela de Opções
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS opcoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ativo TEXT NOT NULL,
            strike REAL,
            tp_opcao TEXT,
            dt_operacao TEXT,
            dt_vencimento TEXT,
            derivativo TEXT,
            quantidade INTEGER,
            vl_opcao REAL,
            vl_premio REAL,
            status TEXT,
            user_id INTEGER NOT NULL DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

def get_user_count():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]

def create_user(username, email, birth_date, password):
    hashed = hash_password(password)
    from datetime import datetime
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, birth_date, password, created_at) VALUES (?, ?, ?, ?, ?)", (username, email, birth_date, hashed, now_str))
        conn.commit()

def verify_user(login_identifier, password):
    """
    Verifica o usuário pelo email ou pelo nome 'admin' (se for o caso).
    Realiza a migração automática de senhas antigas para o padrão bcrypt.
    Retorna (sucesso, id, username).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if login_identifier == 'admin':
            cursor.execute("SELECT id, username, password FROM users WHERE username = ?", (login_identifier,))
        else:
            cursor.execute("SELECT id, username, password FROM users WHERE email = ?", (login_identifier,))
        
        row = cursor.fetchone()
        
        if not row:
            return (False, None, None)
            
        user_id, username, hashed_password = row
        is_valid, needs_rehash = verify_password(password, hashed_password)
        
        if is_valid:
            if needs_rehash:
                # Rehash in background without interrupting user flow
                new_hash = hash_password(password)
                cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_hash, user_id))
                conn.commit()
            return True, user_id, username
            
        return False, None, None

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    try:
        yield conn
    finally:
        conn.close()

def recalculate_asset_balance(asset_id, conn):
    """Recalcula a quantidade e o preço médio de um ativo com base no histórico."""
    cursor = conn.cursor()
    cursor.execute("SELECT quantity, unit_price FROM asset_history WHERE asset_id = ?", (asset_id,))
    history = cursor.fetchall()
    
    total_quantity = 0.0
    total_cost = 0.0
    
    for qty, price in history:
        total_quantity += qty
        if qty > 0: # Compra: aumenta o custo total
            total_cost += qty * price
            
    cursor.execute("SELECT SUM(quantity), SUM(quantity * unit_price) FROM asset_history WHERE asset_id = ? AND quantity > 0", (asset_id,))
    total_buy_qty, total_buy_cost = cursor.fetchone()
    
    avg_price = total_buy_cost / total_buy_qty if total_buy_qty and total_buy_qty > 0 else 0.0
    
    cursor.execute("SELECT SUM(quantity) FROM asset_history WHERE asset_id = ?", (asset_id,))
    final_qty = cursor.fetchone()[0] or 0.0
    
    cursor.execute(
        "UPDATE assets SET quantity = ?, average_price = ? WHERE id = ?",
        (final_qty, avg_price, asset_id)
    )

def add_empty_asset(ticker, asset_type, user_id):
    ticker = ticker.upper()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE ticker = ? AND user_id = ?", (ticker, user_id))
        existing_asset = cursor.fetchone()
        
        if not existing_asset:
            cursor.execute(
                "INSERT INTO assets (ticker, asset_type, quantity, average_price, user_id) VALUES (?, ?, 0, 0, ?)",
                (ticker, asset_type, user_id)
            )
            conn.commit()
            return True
        return False

def get_asset_by_id(asset_id, user_id):
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assets WHERE id = ? AND user_id = ?", (asset_id, user_id))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_asset_operation(asset_id, user_id, date, quantity, unit_price):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE id = ? AND user_id = ?", (asset_id, user_id))
        if cursor.fetchone():
            cursor.execute(
                "INSERT INTO asset_history (asset_id, date, quantity, unit_price) VALUES (?, ?, ?, ?)",
                (asset_id, date, quantity, unit_price)
            )
            recalculate_asset_balance(asset_id, conn)
            conn.commit()

def update_asset_operation(operation_id, asset_id, user_id, date, quantity, unit_price):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE id = ? AND user_id = ?", (asset_id, user_id))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE asset_history SET date = ?, quantity = ?, unit_price = ? WHERE id = ? AND asset_id = ?",
                (date, quantity, unit_price, operation_id, asset_id)
            )
            recalculate_asset_balance(asset_id, conn)
            conn.commit()

def delete_asset_operation(operation_id, asset_id, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE id = ? AND user_id = ?", (asset_id, user_id))
        if cursor.fetchone():
            cursor.execute("DELETE FROM asset_history WHERE id = ? AND asset_id = ?", (operation_id, asset_id))
            recalculate_asset_balance(asset_id, conn)
            conn.commit()


def add_or_update_fixed_income_asset(ticker, saldo, user_id):
    ticker = ticker.upper()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE ticker = ? AND user_id = ?", (ticker, user_id))
        existing_asset = cursor.fetchone()
        
        if existing_asset:
            asset_id = existing_asset[0]
            cursor.execute(
                "UPDATE assets SET quantity = 1, average_price = ?, asset_type = 'Renda Fixa' WHERE id = ? AND user_id = ?",
                (saldo, asset_id, user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO assets (ticker, asset_type, quantity, average_price, user_id) VALUES (?, 'Renda Fixa', 1, ?, ?)",
                (ticker, saldo, user_id)
            )
        conn.commit()

def save_provento(ano, mes, ticker, valor, user_id):
    ano = int(ano)
    ticker = str(ticker).strip().upper()
    valor = float(valor)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM proventos WHERE ano = ? AND mes = ? AND ticker = ? AND user_id = ?", (ano, mes, ticker, user_id))
        res = cursor.fetchone()
        
        if res:
            cursor.execute("UPDATE proventos SET valor = ? WHERE id = ? AND user_id = ?", (valor, res[0], user_id))
        else:
            cursor.execute("INSERT INTO proventos (ano, mes, ticker, valor, user_id) VALUES (?, ?, ?, ?, ?)", (ano, mes, ticker, valor, user_id))
        conn.commit()

def delete_proventos_ativo_ano(ano, ticker, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM proventos WHERE ano = ? AND ticker = ? AND user_id = ?", (ano, ticker, user_id))
        conn.commit()

def get_all_assets(user_id):
    with get_db_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM assets WHERE user_id = ? AND (quantity > 0 OR asset_type = 'Renda Fixa')", conn, params=(user_id,))
    return df

def get_asset_history(asset_id, user_id):
    with get_db_connection() as conn:
        query = '''
            SELECT h.* FROM asset_history h 
            JOIN assets a ON h.asset_id = a.id 
            WHERE a.id = ? AND a.user_id = ? 
            ORDER BY h.date DESC
        '''
        df = pd.read_sql_query(query, conn, params=(asset_id, user_id))
    return df

def get_proventos(user_id):
    import struct
    with get_db_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM proventos WHERE user_id = ? ORDER BY ano DESC, mes, ticker", conn, params=(user_id,))
    if not df.empty:
        def safe_int_ano(val):
            if isinstance(val, bytes):
                try:
                    return struct.unpack('<q', val)[0]
                except Exception:
                    return int.from_bytes(val, byteorder='little')
            return int(val)
        df['ano'] = df['ano'].apply(safe_int_ano)
    return df

def update_asset(asset_id, user_id, ticker, asset_type, quantity, average_price, price_ceiling=0, fair_value=0):
    ticker = ticker.upper()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if asset_type == 'Renda Fixa':
            cursor.execute(
                "UPDATE assets SET ticker = ?, asset_type = ?, quantity = ?, average_price = ?, price_ceiling = ?, fair_value = ? WHERE id = ? AND user_id = ?",
                (ticker, asset_type, quantity, average_price, price_ceiling, fair_value, asset_id, user_id)
            )
        else:
            cursor.execute(
                "UPDATE assets SET ticker = ?, asset_type = ?, price_ceiling = ?, fair_value = ? WHERE id = ? AND user_id = ?",
                (ticker, asset_type, price_ceiling, fair_value, asset_id, user_id)
            )
        conn.commit()

def delete_asset(asset_id, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE id = ? AND user_id = ?", (asset_id, user_id))
        if cursor.fetchone():
            cursor.execute("DELETE FROM asset_history WHERE asset_id = ?", (asset_id,))
            cursor.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
            conn.commit()

def import_from_csv(file_path, user_id):
    import csv
    import os
    if not os.path.exists(file_path):
        return False, "Arquivo não encontrado."
    
    try:
        with open(file_path, mode='r', encoding='ISO-8859-1') as f:
            reader = csv.reader(f, delimiter=';')
            try:
                header = next(reader)
            except StopIteration:
                return False, "Arquivo vazio."
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ticker, id FROM assets WHERE user_id = ?", (user_id,))
                assets_map = {row[0]: row[1] for row in cursor.fetchall()}
                
                for row in reader:
                    if not row or len(row) < 5:
                        continue
                        
                    ticker = row[0].strip().upper()
                    asset_type = row[1].strip()
                    date = row[2].strip()
                    
                    if '/' in date:
                        parts = date.split('/')
                        if len(parts) == 3:
                            year = parts[2]
                            if len(year) == 2: year = "20" + year
                            date = f"{year}-{parts[1]}-{parts[0]}"
                    
                    try:
                        quantity = float(row[3].replace(',', '.'))
                        unit_price = float(row[4].replace(',', '.'))
                    except (ValueError, IndexError):
                        continue
                    
                    if ticker not in assets_map:
                        cursor.execute(
                            "INSERT INTO assets (ticker, asset_type, quantity, average_price, user_id) VALUES (?, ?, 0, 0, ?)",
                            (ticker, asset_type, user_id)
                        )
                        assets_map[ticker] = cursor.lastrowid
                    
                    asset_id = assets_map[ticker]
                    cursor.execute(
                        "INSERT INTO asset_history (asset_id, date, quantity, unit_price) VALUES (?, ?, ?, ?)",
                        (asset_id, date, quantity, unit_price)
                    )
                
                for asset_id in assets_map.values():
                    recalculate_asset_balance(asset_id, conn)
                
                conn.commit()
        return True, "Importação concluída com sucesso."
    except Exception as e:
        return False, f"Erro ao importar: {str(e)}"

def import_proventos_csv(file_content, user_id):
    import csv
    import io
    
    meses_map = {
        'Jan': 'Janeiro', 'Feb': 'Fevereiro', 'Mar': 'Março', 'Apr': 'Abril',
        'May': 'Maio', 'Jun': 'Junho', 'Jul': 'Julho', 'Aug': 'Agosto',
        'Sep': 'Setembro', 'Oct': 'Outubro', 'Nov': 'Novembro', 'Dec': 'Dezembro'
    }
    
    try:
        # Prepara o conteúdo do arquivo
        if isinstance(file_content, str):
            import os
            if not os.path.exists(file_content):
                return False, "Arquivo não encontrado."
            f = open(file_content, mode='r', encoding='utf-8')
        else:
            if hasattr(file_content, 'getvalue'):
                content = file_content.getvalue()
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                f = io.StringIO(content)
            else:
                f = file_content

        # 1. Validação do Layout (sem deletar nada ainda)
        content_for_validation = f.read()
        f.seek(0)
        
        validation_f = io.StringIO(content_for_validation)
        reader = csv.reader(validation_f, delimiter=',')
        try:
            header = next(reader)
            if not header or len(header) < 14: # Ano, Ativo + 12 meses
                return False, "Layout do arquivo de Proventos inválido (faltam colunas)."
            
            # Valida primeira linha de dados se existir
            first_row = next(reader, None)
            if first_row:
                if not first_row[0].isdigit() or len(first_row[0]) != 4:
                    return False, f"Layout inválido: O ano '{first_row[0]}' deve ter 4 dígitos."
        except Exception as ve:
            return False, f"Erro na validação do layout: {str(ve)}"

        # 2. Processo de Importação com Transação
        with get_db_connection() as conn:
            conn.isolation_level = None # Manual transaction control
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            try:
                # Deleta dados atuais
                cursor.execute("DELETE FROM proventos WHERE user_id = ?", (user_id,))
                
                # Reinicia o reader ( StringIO já foi seek(0) )
                reader = csv.reader(io.StringIO(content_for_validation), delimiter=',')
                next(reader) # pular cabeçalho
                
                meses_colunas = [col.strip() for col in header[2:]]
                
                for row in reader:
                    if not row or len(row) < 3:
                        continue
                        
                    ano = int(row[0].strip())
                    ticker = row[1].strip().upper()
                    if "." not in ticker and len(ticker) >= 4:
                        ticker += ".SA"
                        
                    for idx, val_str in enumerate(row[2:]):
                        val_str = val_str.strip()
                        if not val_str:
                            continue
                            
                        if idx < len(meses_colunas):
                            mes_original = meses_colunas[idx]
                            mes_pt = meses_map.get(mes_original, mes_original)
                            val_clean = val_str.replace('R$', '').replace('$', '').replace(',', '.').strip()
                            valor = float(val_clean)
                            
                            if valor > 0:
                                cursor.execute(
                                    "INSERT INTO proventos (ano, mes, ticker, valor, user_id) VALUES (?, ?, ?, ?, ?)",
                                    (ano, mes_pt, ticker, valor, user_id)
                                )
                
                cursor.execute("COMMIT")
                return True, "Importação de Proventos concluída com sucesso."
                
            except Exception as e:
                cursor.execute("ROLLBACK")
                return False, f"Erro durante a importação (Operação Cancelada): {str(e)}"
    except Exception as e:
        return False, f"Erro ao processar o arquivo: {str(e)}"
    finally:
        if isinstance(file_content, str) and 'f' in locals():
            f.close()

def import_assets_csv(file_content, user_id):
    import csv
    import io
    from datetime import datetime
    try:
        # Prepara o conteúdo do arquivo
        if isinstance(file_content, str):
            import os
            if not os.path.exists(file_content):
                return False, "Arquivo não encontrado."
            f = open(file_content, mode='r', encoding='utf-8')
        else:
            if hasattr(file_content, 'getvalue'):
                content = file_content.getvalue()
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                f = io.StringIO(content)
            else:
                f = file_content

        # 1. Validação do Layout
        content_for_validation = f.read()
        f.seek(0)
        
        validation_f = io.StringIO(content_for_validation)
        reader = csv.reader(validation_f, delimiter=',')
        try:
            header = next(reader)
            if not header or len(header) < 4:
                return False, "Layout do arquivo de Ativos inválido (faltam colunas: Ativo, Data, Quantidade, Valor)."
            
            # Valida primeira linha de dados
            first_row = next(reader, None)
            if first_row:
                try:
                    datetime.strptime(first_row[1].strip(), '%d/%m/%Y')
                except ValueError:
                    return False, f"Layout inválido: A data '{first_row[1]}' deve estar no formato DD/MM/AAAA."
        except Exception as ve:
            return False, f"Erro na validação do layout: {str(ve)}"

        # 2. Processo de Importação com Transação
        with get_db_connection() as conn:
            conn.isolation_level = None # Manual transaction control
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            try:
                # Deleta dados atuais (Ativos e Histórico)
                cursor.execute("DELETE FROM asset_history WHERE asset_id IN (SELECT id FROM assets WHERE user_id = ?)", (user_id,))
                cursor.execute("DELETE FROM assets WHERE user_id = ?", (user_id,))
                
                # Reinicia o reader
                reader = csv.reader(io.StringIO(content_for_validation), delimiter=',')
                next(reader) # pular cabeçalho
                
                # Cache para IDs de ativos criados durante esta importação
                assets_map = {}
                
                for row in reader:
                    if not row or len(row) < 4:
                        continue
                    
                    ticker = row[0].strip().upper()
                    if "." not in ticker and len(ticker) >= 4:
                        ticker += ".SA"
                    
                    db_date = datetime.strptime(row[1].strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                    quantity = float(row[2].strip().replace(',', '.'))
                    unit_price = float(row[3].strip().replace(',', '.'))
                    
                    if ticker not in assets_map:
                        asset_type = infer_asset_type(ticker)
                        cursor.execute(
                            "INSERT INTO assets (ticker, asset_type, quantity, average_price, user_id) VALUES (?, ?, 0, 0, ?)",
                            (ticker, asset_type, user_id)
                        )
                        assets_map[ticker] = cursor.lastrowid
                    
                    asset_id = assets_map[ticker]
                    cursor.execute(
                        "INSERT INTO asset_history (asset_id, date, quantity, unit_price) VALUES (?, ?, ?, ?)",
                        (asset_id, db_date, quantity, unit_price)
                    )
                
                # Recalcula saldos finais
                for aid in assets_map.values():
                    recalculate_asset_balance(aid, conn)
                
                cursor.execute("COMMIT")
                return True, "Importação de Ativos concluída com sucesso."
                
            except Exception as e:
                cursor.execute("ROLLBACK")
                return False, f"Erro durante a importação (Operação Cancelada): {str(e)}"
                
    except Exception as e:
        return False, f"Erro ao processar o arquivo: {str(e)}"
    finally:
        if isinstance(file_content, str) and 'f' in locals():
            f.close()

def get_total_proventos_by_ticker(ticker, user_id):
    ticker = ticker.strip().upper()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(valor) FROM proventos WHERE ticker = ? AND user_id = ?", (ticker, user_id))
        res = cursor.fetchone()
        return res[0] if res[0] is not None else 0.0

def check_and_create_next_year_dashboard(user_id):
    from datetime import datetime
    now = datetime.now()
    current_year = now.year
    next_year = current_year + 1
    
    if now.month == 12:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM proventos WHERE ano = ? AND user_id = ? LIMIT 1", (next_year, user_id))
            if cursor.fetchone() is None:
                cursor.execute("SELECT DISTINCT ticker FROM proventos WHERE ano = ? AND user_id = ?", (current_year, user_id))
                tickers = cursor.fetchall()
                if not tickers:
                    cursor.execute("SELECT DISTINCT ticker FROM assets WHERE user_id = ?", (user_id,))
                    tickers = cursor.fetchall()
                
                for row in tickers:
                    ticker = row[0]
                    cursor.execute(
                        "INSERT INTO proventos (ano, mes, ticker, valor, user_id) VALUES (?, 'Janeiro', ?, 0.0, ?)",
                        (next_year, ticker, user_id)
                    )
                conn.commit()
                return True
    return False

def get_all_total_proventos(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(valor) FROM proventos WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        return res[0] if res[0] is not None else 0.0

def get_all_proventos(user_id):
    with get_db_connection() as conn:
        return pd.read_sql_query("SELECT * FROM proventos WHERE user_id = ?", conn, params=(user_id,))

def import_opcoes_tsv(file_path, user_id):
    import csv
    import os
    if not os.path.exists(file_path):
        return False, "Arquivo não encontrado."
    
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            try:
                header = next(reader)
            except StopIteration:
                return False, "Arquivo vazio."
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM opcoes WHERE user_id = ?", (user_id,))
                
                for row in reader:
                    if not row or len(row) < 10:
                        continue
                        
                    ativo = row[0].strip().upper()
                    if not ativo.endswith(".SA"):
                        ativo += ".SA"
                        
                    try:
                        def parse_currency(val_str):
                            if not val_str: return 0.0
                            val_str = val_str.replace('$', '').strip()
                            val_str = val_str.replace('.', '')
                            val_str = val_str.replace(',', '.')
                            return float(val_str)
                            
                        strike = parse_currency(row[1])
                        tp_opcao = row[2].strip()
                        
                        dt_operacao = row[3].strip()
                        if '/' in dt_operacao:
                            p = dt_operacao.split('/')
                            if len(p) == 3: 
                                year = p[2]
                                if len(year) == 2: year = "20" + year
                                dt_operacao = f"{year}-{p[1]}-{p[0]}"
                                
                        dt_vencimento = row[4].strip()
                        if '/' in dt_vencimento:
                            p = dt_vencimento.split('/')
                            if len(p) == 3: 
                                year = p[2]
                                if len(year) == 2: year = "20" + year
                                dt_vencimento = f"{year}-{p[1]}-{p[0]}"
                                
                        derivativo = row[5].strip()
                        quantidade = int(parse_currency(row[6]))
                        vl_opcao = parse_currency(row[7])
                        vl_premio = parse_currency(row[8])
                        status = row[9].strip()
                        
                        cursor.execute('''
                            INSERT INTO opcoes (ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, user_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, user_id))
                    except (ValueError, IndexError):
                        continue
                
                conn.commit()
        return True, "Importação de Opções concluída com sucesso."
    except Exception as e:
        return False, f"Erro ao importar Opções: {str(e)}"

def get_opcoes(user_id):
    with get_db_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM opcoes WHERE user_id = ? ORDER BY dt_vencimento ASC, ativo ASC", conn, params=(user_id,))
    return df

def insert_opcao(ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO opcoes (ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, user_id))
        conn.commit()

def update_opcao(opcao_id, user_id, ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE opcoes 
            SET ativo=?, strike=?, tp_opcao=?, dt_operacao=?, dt_vencimento=?, derivativo=?, quantidade=?, vl_opcao=?, vl_premio=?, status=?
            WHERE id=? AND user_id=?
        ''', (ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, opcao_id, user_id))
        conn.commit()

def delete_opcao(opcao_id, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM opcoes WHERE id=? AND user_id=?", (opcao_id, user_id))
        conn.commit()

def get_all_users():
    with get_db_connection() as conn:
        df = pd.read_sql_query("SELECT id, username, email, birth_date, created_at FROM users", conn)
    return df

def admin_create_user(username, email, birth_date, password):
    hashed = hash_password(password)
    from datetime import datetime
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, birth_date, password, created_at) VALUES (?, ?, ?, ?, ?)", (username, email, birth_date, hashed, now_str))
        conn.commit()

def admin_update_user(user_id, username, email, birth_date, new_password=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if new_password:
            hashed = hash_password(new_password)
            cursor.execute("UPDATE users SET username = ?, email = ?, birth_date = ?, password = ? WHERE id = ?", (username, email, birth_date, hashed, user_id))
        else:
            cursor.execute("UPDATE users SET username = ?, email = ?, birth_date = ? WHERE id = ?", (username, email, birth_date, user_id))
        conn.commit()

def admin_delete_user(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM asset_history WHERE asset_id IN (SELECT id FROM assets WHERE user_id = ?)", (user_id,))
        cursor.execute("DELETE FROM assets WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM proventos WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM opcoes WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

def get_user_details(user_id):
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, birth_date, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_user_profile(user_id, username, email, birth_date, password=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if password:
            hashed = hash_password(password)
            cursor.execute("UPDATE users SET username = ?, email = ?, birth_date = ?, password = ? WHERE id = ?", (username, email, birth_date, hashed, user_id))
        else:
            cursor.execute("UPDATE users SET username = ?, email = ?, birth_date = ? WHERE id = ?", (username, email, birth_date, user_id))
        conn.commit()

def update_user_password(user_id, new_password):
    hashed = hash_password(new_password)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
        conn.commit()
