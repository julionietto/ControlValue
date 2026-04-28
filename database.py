import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
load_dotenv()
import pandas as pd
import numpy as np
from psycopg2.extensions import register_adapter, AsIs
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Variável global para controle da thread de desbloqueio
_unblock_thread_active = False

def _unblock_worker():
    """Worker que roda em segundo plano para limpar bloqueios expirados."""
    global _unblock_thread_active
    while True:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Remove bloqueios expirados
                sp_tz = ZoneInfo("America/Sao_Paulo")
                cursor.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE locked_until IS NOT NULL AND locked_until <= %s", (datetime.now(sp_tz).replace(tzinfo=None),))
                conn.commit()
                
                # Verifica se ainda existe algum usuário bloqueado
                cursor.execute("SELECT COUNT(*) FROM users WHERE locked_until IS NOT NULL")
                count = cursor.fetchone()[0]
                
            if count == 0:
                _unblock_thread_active = False
                break
        except Exception as e:
            print(f"Erro na thread de desbloqueio: {e}")
            
        time.sleep(60)

def trigger_unblock_thread():
    """Inicia a thread de desbloqueio se ela não estiver ativa."""
    global _unblock_thread_active
    if not _unblock_thread_active:
        _unblock_thread_active = True
        thread = threading.Thread(target=_unblock_worker, daemon=True)
        thread.start()

# Adaptadores para resolver incompatibilidade entre Numpy/Pandas e Psycopg2
register_adapter(np.int64, lambda val: AsIs(int(val)))
register_adapter(np.float64, lambda val: AsIs(float(val)))

import hashlib
import bcrypt
from contextlib import contextmanager
import streamlit as st
from psycopg2 import pool

def get_database_url():
    """Busca a URL no secrets (Streamlit Cloud) ou no .env (Local)."""
    try:
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception as e:
        import logging
        logging.warning(f"Aviso ao acessar DATABASE_URL no st.secrets: {e}")
    return os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/controlvalue")

@st.cache_resource(ttl=3600)
def init_connection_pool():
    """Inicializa um Connection Pool com suporte a SSL para Cloud."""
    db_url = get_database_url()
    if "127.0.0.1" not in db_url and "localhost" not in db_url and "sslmode=" not in db_url:
        db_url += "?sslmode=require" if "?" not in db_url else "&sslmode=require"
    return pool.ThreadedConnectionPool(1, 20, db_url)

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
    db_pool = init_connection_pool()
    conn = db_pool.getconn()
    cursor = conn.cursor()
    # Tabela de Ativos (consolidado)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id SERIAL PRIMARY KEY,
            ticker TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            quantity REAL NOT NULL,
            average_price REAL NOT NULL,
            price_ceiling REAL DEFAULT 0,
            fair_value REAL DEFAULT 0,
            user_id INTEGER NOT NULL DEFAULT 1,
            currency TEXT NOT NULL DEFAULT 'BRL'
        )
    ''')
    # Tabela de Histórico de Operações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asset_history (
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT,
            birth_date TEXT,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            failed_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP
        )
    ''')
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_attempts INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP")
        
        # Migração da coluna de Moeda (v1.2.1)
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='assets' AND column_name='currency'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE assets ADD COLUMN currency TEXT NOT NULL DEFAULT 'BRL'")
            # Regra de Migração solicitada: Stocks/Reits = USD, resto = BRL (especialmente Cripto para user 1)
            cursor.execute("UPDATE assets SET currency = 'USD' WHERE asset_type IN ('Stocks', 'Reits')")
            cursor.execute("UPDATE assets SET currency = 'BRL' WHERE asset_type IN ('Ações', 'Fiis', 'Renda Fixa', 'Cripto')")
            
    except Exception as e:
        import logging
        logging.warning(f"Aviso na atualização do schema: {e}")
    # Tabela de Proventos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proventos (
            id SERIAL PRIMARY KEY,
            ano INTEGER NOT NULL,
            mes INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            valor REAL NOT NULL,
            user_id INTEGER NOT NULL DEFAULT 1
        )
    ''')
    
    try:
        # Migração Segura para INTEGER na coluna mes
        cursor.execute("SELECT data_type FROM information_schema.columns WHERE table_name='proventos' AND column_name='mes'")
        mes_type = cursor.fetchone()
        if mes_type and mes_type[0] == 'text':
            cursor.execute("""
                UPDATE proventos SET mes = 
                CASE 
                    WHEN mes = 'Janeiro' THEN '1'
                    WHEN mes = 'Fevereiro' THEN '2'
                    WHEN mes = 'Março' THEN '3'
                    WHEN mes = 'Abril' THEN '4'
                    WHEN mes = 'Maio' THEN '5'
                    WHEN mes = 'Junho' THEN '6'
                    WHEN mes = 'Julho' THEN '7'
                    WHEN mes = 'Agosto' THEN '8'
                    WHEN mes = 'Setembro' THEN '9'
                    WHEN mes = 'Outubro' THEN '10'
                    WHEN mes = 'Novembro' THEN '11'
                    WHEN mes = 'Dezembro' THEN '12'
                    ELSE '1'
                END
            """)
            cursor.execute("ALTER TABLE proventos ALTER COLUMN mes TYPE INTEGER USING mes::integer")
    except Exception as e:
        import logging
        logging.warning(f"Aviso na migração de meses do proventos: {e}")
    # Tabela de Opções
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS opcoes (
            id SERIAL PRIMARY KEY,
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
    # Tabela de Password Resets
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_resets (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    # Tabela de Logs de Sincronização (Background Job)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_logs (
            id SERIAL PRIMARY KEY,
            sync_date TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT,
            execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Tabela de Proventos Provisionados (Futuros)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proventos_provisionados (
            id SERIAL PRIMARY KEY,
            ticker TEXT NOT NULL,
            tipo TEXT NOT NULL,
            data_com DATE NOT NULL,
            data_pagamento DATE NOT NULL,
            valor REAL NOT NULL,
            user_id INTEGER NOT NULL DEFAULT 1
        )
    ''')
    
    # Tabela de Alocação de Classes de Ativos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_allocations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            asset_class TEXT NOT NULL,
            allocation_percent REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, asset_class)
        )
    ''')
    
    try:
        # Migração Segura para DATE
        cursor.execute("SELECT data_type FROM information_schema.columns WHERE table_name='proventos_provisionados' AND column_name='data_com'")
        dt_type = cursor.fetchone()
        if dt_type and dt_type[0] == 'text':
            cursor.execute("ALTER TABLE proventos_provisionados ALTER COLUMN data_com TYPE DATE USING to_date(data_com, 'DD/MM/YYYY')")
            cursor.execute("ALTER TABLE proventos_provisionados ALTER COLUMN data_pagamento TYPE DATE USING to_date(data_pagamento, 'DD/MM/YYYY')")
    except Exception as e:
        import logging
        logging.warning(f"Aviso na migração de datas do proventos_provisionados: {e}")
        
    conn.commit()
    db_pool = init_connection_pool()
    db_pool.putconn(conn)

def get_user_count():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]

def create_user(username, email, birth_date, password):
    if username.lower().strip() == 'admin':
        if get_user_count() > 0:
            raise ValueError("O nome de usuário 'admin' é reservado.")
        
    hashed = hash_password(password)
    from datetime import datetime
    sp_tz = ZoneInfo("America/Sao_Paulo")
    now_str = datetime.now(sp_tz).strftime('%Y-%m-%d %H:%M:%S')
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, birth_date, password, created_at) VALUES (%s, %s, %s, %s, %s)", (username, email, birth_date, hashed, now_str))
        conn.commit()

def verify_user(login_identifier, password):
    """
    Verifica o usuário pelo email ou pelo nome 'admin' (se for o caso).
    Realiza a migração automática de senhas antigas para o padrão bcrypt.
    Retorna (sucesso, id, username, is_admin, status_code, extra_info).
    status_code: 'SUCCESS', 'WRONG_PASS', 'LOCKED', 'NOT_FOUND'
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if login_identifier == 'admin':
            cursor.execute("SELECT id, username, password, email, birth_date, failed_attempts, locked_until FROM users WHERE username = %s", (login_identifier,))
        else:
            cursor.execute("SELECT id, username, password, email, birth_date, failed_attempts, locked_until FROM users WHERE email = %s", (login_identifier,))
        
        row = cursor.fetchone()
        
        if not row:
            return False, None, None, False, 'NOT_FOUND', None
            
        user_id, username, hashed_password, email, birth_date, failed_attempts, locked_until = row
        
        # 1. Verifica se está bloqueado
        if locked_until:
            sp_tz = ZoneInfo("America/Sao_Paulo")
            # locked_until do BD vem como naive se não for timestamptz. Tratamos como naive SP para comparação rápida.
            if datetime.now(sp_tz).replace(tzinfo=None) < locked_until:
                return False, user_id, username, False, 'LOCKED', locked_until
            else:
                # Bloqueio expirou "na hora" (lazy unblock)
                cursor.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = %s", (user_id,))
                conn.commit()
                failed_attempts = 0
                locked_until = None
        
        is_valid, needs_rehash = verify_password(password, hashed_password)
        
        if is_valid:
            # 2. Login de Sucesso - Reseta falhas
            cursor.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = %s", (user_id,))
            if needs_rehash:
                new_hash = hash_password(password)
                cursor.execute("UPDATE users SET password = %s WHERE id = %s", (new_hash, user_id))
            conn.commit()
            
            # O admin real não tem email e nascimento definidos
            is_admin_flag = (username == 'admin' and (not email or email.strip() == "") and (not birth_date or birth_date.strip() == ""))
            return True, user_id, username, is_admin_flag, 'SUCCESS', None
            
        else:
            # 3. Falha de Senha - Incrementa tentativas
            new_failed = failed_attempts + 1
            new_locked_until = None
            
            if new_failed >= 3:
                sp_tz = ZoneInfo("America/Sao_Paulo")
                new_locked_until = datetime.now(sp_tz).replace(tzinfo=None) + timedelta(minutes=5)
                # Dispara a thread de desbloqueio em background
                trigger_unblock_thread()
            
            cursor.execute("UPDATE users SET failed_attempts = %s, locked_until = %s WHERE id = %s", (new_failed, new_locked_until, user_id))
            conn.commit()
            
            return False, user_id, username, False, 'WRONG_PASS', new_locked_until

def get_user_by_email(email):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT id, username, email FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_password_reset_token(user_id, token, expires_in_minutes=30):
    from datetime import datetime, timedelta
    sp_tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(sp_tz).replace(tzinfo=None)
    expires_at = now + timedelta(minutes=expires_in_minutes)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Invalida tokens antigos do usuário
        cursor.execute("UPDATE password_resets SET used = TRUE WHERE user_id = %s AND used = FALSE", (user_id,))
        
        cursor.execute(
            "INSERT INTO password_resets (user_id, token, created_at, expires_at, used) VALUES (%s, %s, %s, %s, FALSE)",
            (user_id, token, now, expires_at)
        )
        conn.commit()

def verify_password_reset_token(token):
    """
    Retorna (is_valid, user_id, message)
    """
    from datetime import datetime
    sp_tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(sp_tz).replace(tzinfo=None)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM password_resets WHERE token = %s", (token,))
        row = cursor.fetchone()
        
        if not row:
            return False, None, "Token inválido ou não encontrado."
            
        if row['used']:
            return False, None, "Este link de recuperação já foi utilizado."
            
        if now > row['expires_at']:
            return False, None, "Este link de recuperação expirou."
            
        return True, row['user_id'], "Token válido."

def reset_password_with_token(token, new_password):
    is_valid, user_id, msg = verify_password_reset_token(token)
    if not is_valid:
        return False, msg
        
    hashed = hash_password(new_password)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Atualiza a senha
        cursor.execute("UPDATE users SET password = %s, failed_attempts = 0, locked_until = NULL WHERE id = %s", (hashed, user_id))
        # Marca o token como usado
        cursor.execute("UPDATE password_resets SET used = TRUE WHERE token = %s", (token,))
        conn.commit()
        
    return True, "Senha redefinida com sucesso."

@contextmanager
def get_db_connection():
    db_pool = init_connection_pool()
    conn = db_pool.getconn()
    try:
        yield conn
        if not conn.closed and not conn.autocommit:
            conn.commit()
    except Exception:
        if not conn.closed and not conn.autocommit:
            conn.rollback()
        raise
    finally:
        if not conn.closed and conn.autocommit:
            conn.autocommit = False
        db_pool.putconn(conn)

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


def add_or_update_fixed_income_asset(ticker, saldo, user_id):
    ticker = ticker.upper()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE ticker = %s AND user_id = %s", (ticker, user_id))
        existing_asset = cursor.fetchone()
        
        if existing_asset:
            asset_id = existing_asset[0]
            cursor.execute(
                "UPDATE assets SET quantity = 1, average_price = %s, asset_type = 'Renda Fixa' WHERE id = %s AND user_id = %s",
                (saldo, asset_id, user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO assets (ticker, asset_type, quantity, average_price, user_id) VALUES (%s, 'Renda Fixa', 1, %s, %s)",
                (ticker, saldo, user_id)
            )
        conn.commit()

def save_provento(ano, mes, ticker, valor, user_id):
    ano = int(ano)
    ticker = str(ticker).strip().upper()
    valor = float(valor)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM proventos WHERE ano = %s AND mes = %s AND ticker = %s AND user_id = %s", (ano, mes, ticker, user_id))
        res = cursor.fetchone()
        
        if res:
            cursor.execute("UPDATE proventos SET valor = %s WHERE id = %s AND user_id = %s", (valor, res[0], user_id))
        else:
            cursor.execute("INSERT INTO proventos (ano, mes, ticker, valor, user_id) VALUES (%s, %s, %s, %s, %s)", (ano, mes, ticker, valor, user_id))
        conn.commit()

def delete_proventos_ativo_ano(ano, ticker, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM proventos WHERE ano = %s AND ticker = %s AND user_id = %s", (ano, ticker, user_id))
        conn.commit()

def get_all_assets(user_id):
    with get_db_connection() as conn:
        df = _query_to_df("SELECT * FROM assets WHERE user_id = %s AND (quantity > 0 OR asset_type = 'Renda Fixa')", conn, params=(user_id,))
    return df

def get_asset_history(asset_id, user_id):
    with get_db_connection() as conn:
        query = '''
            SELECT h.* FROM asset_history h 
            JOIN assets a ON h.asset_id = a.id 
            WHERE a.id = %s AND a.user_id = %s 
            ORDER BY CAST(h.date AS DATE) ASC
        '''
        df = _query_to_df(query, conn, params=(asset_id, user_id))
    return df

def get_all_asset_histories(user_id):
    """Busca o histórico de operações de TODOS os ativos do usuário em um único Round-Trip para evitar Overhead N+1"""
    with get_db_connection() as conn:
        query = '''
            SELECT h.* FROM asset_history h 
            JOIN assets a ON h.asset_id = a.id 
            WHERE a.user_id = %s 
            ORDER BY h.date ASC
        '''
        df = _query_to_df(query, conn, params=(user_id,))
    return df

def get_proventos(user_id):
    import struct
    with get_db_connection() as conn:
        df = _query_to_df("SELECT * FROM proventos WHERE user_id = %s ORDER BY ano DESC, mes, ticker", conn, params=(user_id,))
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

def get_proventos_provisionados_calculados(user_id):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    hoje_sp = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    
    with get_db_connection() as conn:
        query = '''
            SELECT
                p.ticker,
                p.tipo,
                p.data_com,
                p.data_pagamento,
                p.valor,
                COALESCE(SUM(h.quantity), 0) as quantidade_elegivel
            FROM proventos_provisionados p
            JOIN assets a ON a.ticker = p.ticker AND a.user_id = p.user_id
            LEFT JOIN asset_history h ON h.asset_id = a.id AND CAST(h.date AS DATE) <= p.data_com
            WHERE p.user_id = %s AND p.data_pagamento >= %s
            GROUP BY p.id, p.ticker, p.tipo, p.data_com, p.data_pagamento, p.valor
            ORDER BY p.data_pagamento ASC, p.ticker ASC
        '''
        df = _query_to_df(query, conn, params=(user_id, hoje_sp))
    return df

def upsert_provento_provisionado(ticker, tipo, data_com, data_pagamento, valor, user_id):
    ticker = str(ticker).strip().upper()
    valor = float(valor)
    
    try:
        dt_com_db = datetime.strptime(data_com, '%d/%m/%Y').strftime('%Y-%m-%d')
        dt_pag_db = datetime.strptime(data_pagamento, '%d/%m/%Y').strftime('%Y-%m-%d')
    except:
        return # Skip se a data não estiver no formato esperado do scraper
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Verifica se já existe um provento idêntico (mesmo ticker e data de pagamento) para atualizar o valor
        cursor.execute(
            "SELECT id FROM proventos_provisionados WHERE ticker = %s AND data_pagamento = %s AND user_id = %s",
            (ticker, dt_pag_db, user_id)
        )
        res = cursor.fetchone()
        
        if res:
            cursor.execute(
                "UPDATE proventos_provisionados SET valor = %s, tipo = %s, data_com = %s WHERE id = %s AND user_id = %s",
                (valor, tipo, dt_com_db, res[0], user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO proventos_provisionados (ticker, tipo, data_com, data_pagamento, valor, user_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (ticker, tipo, dt_com_db, dt_pag_db, valor, user_id)
            )
        conn.commit()

def sync_proventos_from_provisionados(user_id):
    """
    Sincroniza a tabela proventos com os valores proventos_provisionados calculados,
    respeitando a regra do mês de Dezembro para pagamentos do ano seguinte.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import pandas as pd
    
    sp_tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(sp_tz)
    current_year = now.year
    current_month = now.month
    
    with get_db_connection() as conn:
        # Busca todos os proventos provisionados calculando a quantidade elegível
        query = '''
            SELECT
                p.ticker,
                p.data_pagamento,
                p.valor,
                COALESCE(SUM(h.quantity), 0) as quantidade_elegivel
            FROM proventos_provisionados p
            JOIN assets a ON a.ticker = p.ticker AND a.user_id = p.user_id
            LEFT JOIN asset_history h ON h.asset_id = a.id AND CAST(h.date AS DATE) <= p.data_com
            WHERE p.user_id = %s
            GROUP BY p.id, p.ticker, p.data_pagamento, p.valor
        '''
        df = _query_to_df(query, conn, params=(user_id,))
        
    if df.empty:
        return

    # Converte data_pagamento para datetime para extrair ano e mês
    df['data_pagamento'] = pd.to_datetime(df['data_pagamento'])
    df['ano_pag'] = df['data_pagamento'].dt.year
    df['mes_pag_num'] = df['data_pagamento'].dt.month
    
    # Calcula total a receber por evento (quantidade acumulada * valor por cota)
    df['total_receber'] = df['valor'] * df['quantidade_elegivel']
    
    # Agrupa por ticker, ano, mes
    grouped = df.groupby(['ticker', 'ano_pag', 'mes_pag_num'])['total_receber'].sum().reset_index()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for index, row in grouped.iterrows():
            ticker = row['ticker']
            ano = int(row['ano_pag'])
            mes_num = int(row['mes_pag_num'])
            total_valor = float(row['total_receber'])
                
            # Regra de negócio: Para proventos provisionados para o ano seguinte, 
            # os valores somente serão atualizados depois do dia 01 de Dezembro do ano corrente.
            if ano > current_year and current_month < 12:
                continue
                
            # Verifica se já existe na tabela proventos
            cursor.execute("SELECT id FROM proventos WHERE ano = %s AND mes = %s AND ticker = %s AND user_id = %s", (ano, mes_num, ticker, user_id))
            res = cursor.fetchone()
            
            if res:
                # Atualiza com o valor exato (sobrepondo valor anterior/manual)
                cursor.execute("UPDATE proventos SET valor = %s WHERE id = %s AND user_id = %s", (total_valor, res[0], user_id))
            else:
                # Insere
                cursor.execute("INSERT INTO proventos (ano, mes, ticker, valor, user_id) VALUES (%s, %s, %s, %s, %s)", (ano, mes_num, ticker, total_valor, user_id))
                
        # Rotina de Limpeza: Remove registros da tabela de provisionados onde a data de pagamento já passou (menor que a data atual)
        hoje_sp = now.date()
        cursor.execute("DELETE FROM proventos_provisionados WHERE user_id = %s AND data_pagamento < %s", (user_id, hoje_sp))
        
        conn.commit()


def log_sync_execution(sync_date, status, details=""):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now_sp = datetime.now(ZoneInfo("America/Sao_Paulo"))
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sync_logs (sync_date, status, details, execution_time) VALUES (%s, %s, %s, %s)",
            (sync_date, status, details, now_sp)
        )
        conn.commit()

def get_last_sync_log():
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM sync_logs ORDER BY execution_time DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

def check_sync_completed_today(sync_date):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM sync_logs WHERE sync_date = %s AND status = 'SUCCESS'", (sync_date,))
        return cursor.fetchone() is not None

def update_asset(asset_id, user_id, ticker, asset_type, quantity, average_price, price_ceiling=0, fair_value=0, currency='BRL'):
    ticker = ticker.upper()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if asset_type == 'Renda Fixa':
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

def delete_asset(asset_id, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, ticker FROM assets WHERE id = %s AND user_id = %s", (asset_id, user_id))
        row = cursor.fetchone()
        if row:
            ticker = row[1]
            cursor.execute("DELETE FROM asset_history WHERE asset_id = %s", (asset_id,))
            cursor.execute("DELETE FROM assets WHERE id = %s", (asset_id,))
            cursor.execute("DELETE FROM proventos WHERE ticker = %s AND user_id = %s", (ticker, user_id))
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
                cursor.execute("SELECT ticker, id FROM assets WHERE user_id = %s", (user_id,))
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
                            "INSERT INTO assets (ticker, asset_type, quantity, average_price, user_id) VALUES (%s, %s, 0, 0, %s)",
                            (ticker, asset_type, user_id)
                        )
                        assets_map[ticker] = cursor.lastrowid
                    
                    asset_id = assets_map[ticker]
                    cursor.execute(
                        "INSERT INTO asset_history (asset_id, date, quantity, unit_price) VALUES (%s, %s, %s, %s)",
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
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
        'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
        'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
        'Janeiro': 1, 'Fevereiro': 2, 'Março': 3, 'Abril': 4,
        'Maio': 5, 'Junho': 6, 'Julho': 7, 'Agosto': 8,
        'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12
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
            conn.autocommit = True # Manual transaction control
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            try:
                # Deleta dados atuais
                cursor.execute("DELETE FROM proventos WHERE user_id = %s", (user_id,))
                
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
                            # Tenta mapear o mes, se não encontrar pega o indice + 1 assumindo a ordem Janeiro a Dezembro
                            mes_pt = meses_map.get(mes_original, idx + 1)
                            val_clean = val_str.replace('R$', '').replace('$', '').replace(',', '.').strip()
                            valor = float(val_clean)
                            
                            if valor > 0:
                                cursor.execute(
                                    "INSERT INTO proventos (ano, mes, ticker, valor, user_id) VALUES (%s, %s, %s, %s, %s)",
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
            conn.autocommit = True # Manual transaction control
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            try:
                # Deleta dados atuais (Ativos e Histórico)
                cursor.execute("DELETE FROM asset_history WHERE asset_id IN (SELECT id FROM assets WHERE user_id = %s)", (user_id,))
                cursor.execute("DELETE FROM assets WHERE user_id = %s", (user_id,))
                
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
                            "INSERT INTO assets (ticker, asset_type, quantity, average_price, user_id) VALUES (%s, %s, 0, 0, %s)",
                            (ticker, asset_type, user_id)
                        )
                        assets_map[ticker] = cursor.lastrowid
                    
                    asset_id = assets_map[ticker]
                    cursor.execute(
                        "INSERT INTO asset_history (asset_id, date, quantity, unit_price) VALUES (%s, %s, %s, %s)",
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
        cursor.execute("SELECT SUM(valor) FROM proventos WHERE ticker = %s AND user_id = %s", (ticker, user_id))
        res = cursor.fetchone()
        return res[0] if res[0] is not None else 0.0

def check_and_create_next_year_dashboard(user_id):
    from datetime import datetime
    sp_tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(sp_tz)
    current_year = now.year
    next_year = current_year + 1
    
    if now.month == 12:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM proventos WHERE ano = %s AND user_id = %s LIMIT 1", (next_year, user_id))
            if cursor.fetchone() is None:
                cursor.execute("SELECT DISTINCT ticker FROM proventos WHERE ano = %s AND user_id = %s", (current_year, user_id))
                tickers = cursor.fetchall()
                if not tickers:
                    cursor.execute("SELECT DISTINCT ticker FROM assets WHERE user_id = %s", (user_id,))
                    tickers = cursor.fetchall()
                
                for row in tickers:
                    ticker = row[0]
                    cursor.execute(
                        "INSERT INTO proventos (ano, mes, ticker, valor, user_id) VALUES (%s, 1, %s, 0.0, %s)",
                        (next_year, ticker, user_id)
                    )
                conn.commit()
                return True
    return False

def get_all_total_proventos(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(valor) FROM proventos WHERE user_id = %s", (user_id,))
        res = cursor.fetchone()
        return res[0] if res[0] is not None else 0.0

def get_all_proventos(user_id):
    with get_db_connection() as conn:
        return _query_to_df("SELECT * FROM proventos WHERE user_id = %s", conn, params=(user_id,))

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
                cursor.execute("DELETE FROM opcoes WHERE user_id = %s", (user_id,))
                
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
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ''', (ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, user_id))
                    except (ValueError, IndexError):
                        continue
                
                conn.commit()
        return True, "Importação de Opções concluída com sucesso."
    except Exception as e:
        return False, f"Erro ao importar Opções: {str(e)}"

def get_opcoes(user_id):
    with get_db_connection() as conn:
        df = _query_to_df("SELECT * FROM opcoes WHERE user_id = %s ORDER BY dt_vencimento ASC, ativo ASC", conn, params=(user_id,))
    return df

def insert_opcao(ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO opcoes (ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, user_id))
        conn.commit()

def update_opcao(opcao_id, user_id, ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE opcoes 
            SET ativo=%s, strike=%s, tp_opcao=%s, dt_operacao=%s, dt_vencimento=%s, derivativo=%s, quantidade=%s, vl_opcao=%s, vl_premio=%s, status=%s
            WHERE id=%s AND user_id=%s
        ''', (ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, opcao_id, user_id))
        conn.commit()

def delete_opcao(opcao_id, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM opcoes WHERE id=%s AND user_id=%s", (opcao_id, user_id))
        conn.commit()

def get_all_users():
    with get_db_connection() as conn:
        df = _query_to_df("SELECT id, username, email, birth_date, created_at, failed_attempts, locked_until FROM users", conn)
    return df

def admin_create_user(username, email, birth_date, password):
    hashed = hash_password(password)
    from datetime import datetime
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, birth_date, password, created_at) VALUES (%s, %s, %s, %s, %s)", (username, email, birth_date, hashed, now_str))
        conn.commit()

def admin_update_user(user_id, username, email, birth_date, new_password=None):
    # Regra de Ouro: Admin real nunca tem e-mail ou nascimento
    if username.lower().strip() == 'admin':
        email = None
        birth_date = None
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if new_password:
            hashed = hash_password(new_password)
            cursor.execute("UPDATE users SET username = %s, email = %s, birth_date = %s, password = %s WHERE id = %s", (username, email, birth_date, hashed, user_id))
        else:
            cursor.execute("UPDATE users SET username = %s, email = %s, birth_date = %s WHERE id = %s", (username, email, birth_date, user_id))
        conn.commit()

def admin_delete_user(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM asset_history WHERE asset_id IN (SELECT id FROM assets WHERE user_id = %s)", (user_id,))
        cursor.execute("DELETE FROM assets WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM proventos WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM opcoes WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()

def admin_unlock_user(user_id):
    """Reseta as tentativas de falha e remove o bloqueio de um usuário."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = %s", (user_id,))
        conn.commit()

def get_user_details(user_id):
    with get_db_connection() as conn:
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT id, username, email, birth_date, created_at FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_user_profile(user_id, username, email, birth_date, password=None):
    # Regra de Ouro: Admin real nunca tem e-mail ou nascimento
    if username.lower().strip() == 'admin':
        email = None
        birth_date = None
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if password:
            hashed = hash_password(password)
            cursor.execute("UPDATE users SET username = %s, email = %s, birth_date = %s, password = %s WHERE id = %s", (username, email, birth_date, hashed, user_id))
        else:
            cursor.execute("UPDATE users SET username = %s, email = %s, birth_date = %s WHERE id = %s", (username, email, birth_date, user_id))
        conn.commit()

def update_user_password(user_id, new_password):
    hashed = hash_password(new_password)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, user_id))
        conn.commit()

def _query_to_df(query, conn, params=None):
    cursor = conn.cursor()
    cursor.execute(query, params) if params else cursor.execute(query)
    data = cursor.fetchall()
    cols = [desc[0] for desc in cursor.description] if cursor.description else []
    import pandas as pd
    return pd.DataFrame(data, columns=cols)

def get_user_allocations(user_id):
    """Retorna as metas de alocação de classes de ativos do usuário no formato de dicionário."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT asset_class, allocation_percent FROM user_allocations WHERE user_id = %s", (user_id,))
        rows = cursor.fetchall()
        
    allocations = {
        'Ações': 0.0,
        'Fiis': 0.0,
        'Ativos Internacionais': 0.0,
        'Criptos': 0.0,
        'Renda Fixa': 0.0
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
