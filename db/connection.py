import psycopg2  # type: ignore # pyrefly: ignore[missing-import]
import psycopg2.extras  # type: ignore
import os
import numpy as np  # type: ignore
from psycopg2.extensions import register_adapter, AsIs
from psycopg2 import pool
from contextlib import contextmanager
# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Carrega variáveis de ambiente se não estiver no Streamlit
load_dotenv()

# Adaptadores para resolver incompatibilidade entre Numpy/Pandas e Psycopg2
register_adapter(np.int64, lambda val: AsIs(int(val)))
register_adapter(np.float64, lambda val: AsIs(float(val)))

def get_database_url():
    """Busca a URL no secrets (Streamlit Cloud) ou no .env (Local)."""
    try:
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception as e:
        import logging
        logging.warning(f"Aviso ao acessar DATABASE_URL no st.secrets: {e}")
    return os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/controlvalue")

# ==============================================================================
# PREMISSA ARQUITETURAL OBRIGATÓRIA - NEON.TECH AUTO-SUSPEND
# ==============================================================================
# O banco de dados PostgreSQL deste projeto está hospedado na Neon.tech.
# REGRA INVIOLÁVEL: O banco de dados NÃO PODE ter conexões ativas ou mantidas em pool
# de forma permanente. Cada função de leitura ou alteração DEVE abrir uma conexão
# e encerrá-la imediatamente (conn.close()) ao finalizar o bloco de execução.
# Isso garante que a Neon.tech coloque o serviço em Auto-Suspend quando o sistema
# estiver ocioso, evitando estouro do limite mensal de 100 horas de computação.
# NÃO REINTRODUZIR POOLS DE CONEXÃO PERSISTENTES SEM ENCERRAMENTO FÍSICO DAS CONEXÕES.
# ==============================================================================

def close_pool(pool_obj=None):
    """Função legada de fechamento de pool (mantida para compatibilidade)."""
    if pool_obj:
        try:
            pool_obj.closeall()
        except Exception as e:
            import logging
            logging.warning(f"Erro ao fechar o pool de conexões: {e}")

def init_connection_pool():
    """Função legada de inicialização de pool (mantida para compatibilidade)."""
    return None

def clear_db_cache():
    """Limpa o cache de dados do Streamlit com segurança se disponível."""
    try:
        st.cache_data.clear()
    except Exception:
        pass

@contextmanager
def get_db_connection():
    """
    Gerenciador de contexto para obter uma conexão direta com o banco de dados.
    A conexão é criada ao entrar no contexto e OBRIGATORIAMENTE FECHADA ao sair (conn.close()),
    garantindo que nenhuma conexão TCP permaneça aberta e permitindo o Auto-Suspend da Neon.tech.
    """
    db_url = get_database_url()
    if "127.0.0.1" not in db_url and "localhost" not in db_url and "sslmode=" not in db_url:
        db_url += "?sslmode=require" if "?" not in db_url else "&sslmode=require"
    
    conn = psycopg2.connect(db_url)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception as e:
            import logging
            logging.warning(f"Erro ao fechar conexão com o banco de dados: {e}")

def init_db():
    """Inicializa as tabelas do banco de dados e executa migrações de schema."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Tabela de Ativos
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
            
            # Migração da coluna de Moeda
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='assets' AND column_name='currency'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE assets ADD COLUMN currency TEXT NOT NULL DEFAULT 'BRL'")
                cursor.execute("UPDATE assets SET currency = 'USD' WHERE asset_type IN ('Stocks', 'Reits')")
                cursor.execute("UPDATE assets SET currency = 'BRL' WHERE asset_type IN ('Ações', 'Fiis', 'ETF', 'Renda Fixa', 'Cripto', 'Fundo CETIP')")
        except Exception as e:
            import logging
            logging.warning(f"Aviso na atualização do schema: {e}")
    
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_proventos_user_ano ON proventos (user_id, ano)")
        
        try:
            cursor.execute("SELECT data_type FROM information_schema.columns WHERE table_name='proventos' AND column_name='mes'")
            mes_type = cursor.fetchone()
            if mes_type and mes_type[0] == 'text':
                cursor.execute("""
                    UPDATE proventos SET mes = 
                    CASE 
                        WHEN mes = 'Janeiro' THEN '1' WHEN mes = 'Fevereiro' THEN '2'
                        WHEN mes = 'Março' THEN '3' WHEN mes = 'Abril' THEN '4'
                        WHEN mes = 'Maio' THEN '5' WHEN mes = 'Junho' THEN '6'
                        WHEN mes = 'Julho' THEN '7' WHEN mes = 'Agosto' THEN '8'
                        WHEN mes = 'Setembro' THEN '9' WHEN mes = 'Outubro' THEN '10'
                        WHEN mes = 'Novembro' THEN '11' WHEN mes = 'Dezembro' THEN '12'
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
                strike REAL, tp_opcao TEXT, dt_operacao DATE, dt_vencimento DATE,
                derivativo TEXT, quantidade INTEGER, vl_opcao REAL, vl_premio REAL,
                status TEXT, user_id INTEGER NOT NULL DEFAULT 1,
                tipo_operacao TEXT,
                qtd_inicial REAL, vl_opcao_inicial REAL, vl_premio_inicial REAL,
                qtd_final REAL, vl_opcao_final REAL, vl_premio_final REAL,
                resultado REAL
            )
        ''')
    
        try:
            cursor.execute("ALTER TABLE opcoes ADD COLUMN IF NOT EXISTS tipo_operacao TEXT")
            cursor.execute("ALTER TABLE opcoes ADD COLUMN IF NOT EXISTS qtd_inicial REAL")
            cursor.execute("ALTER TABLE opcoes ADD COLUMN IF NOT EXISTS vl_opcao_inicial REAL")
            cursor.execute("ALTER TABLE opcoes ADD COLUMN IF NOT EXISTS vl_premio_inicial REAL")
            cursor.execute("ALTER TABLE opcoes ADD COLUMN IF NOT EXISTS qtd_final REAL")
            cursor.execute("ALTER TABLE opcoes ADD COLUMN IF NOT EXISTS vl_opcao_final REAL")
            cursor.execute("ALTER TABLE opcoes ADD COLUMN IF NOT EXISTS vl_premio_final REAL")
            cursor.execute("ALTER TABLE opcoes ADD COLUMN IF NOT EXISTS resultado REAL")
            
            # Migração de dados para registros abertos
            cursor.execute("""
                UPDATE opcoes 
                SET qtd_inicial = quantidade, 
                    vl_opcao_inicial = vl_opcao, 
                    vl_premio_inicial = vl_premio,
                    tipo_operacao = 'VENDA'
                WHERE status = 'Aberta' AND qtd_inicial IS NULL
            """)
    
            # Migração das colunas dt_operacao e dt_vencimento para DATE
            cursor.execute("SELECT data_type FROM information_schema.columns WHERE table_name='opcoes' AND column_name='dt_operacao'")
            dt_type = cursor.fetchone()
            if dt_type and dt_type[0] in ['text', 'character varying']:
                cursor.execute("ALTER TABLE opcoes ALTER COLUMN dt_operacao TYPE DATE USING NULLIF(dt_operacao, '')::DATE")
                cursor.execute("ALTER TABLE opcoes ALTER COLUMN dt_vencimento TYPE DATE USING NULLIF(dt_vencimento, '')::DATE")
        except Exception as e:
            import logging
            logging.warning(f"Aviso na migração da tabela opcoes: {e}")
    
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
    
        # Tabela de Logs de Sincronização
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_logs (
                id SERIAL PRIMARY KEY,
                sync_date TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
        # Tabela de Proventos Provisionados
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
            cursor.execute("SELECT data_type FROM information_schema.columns WHERE table_name='proventos_provisionados' AND column_name='data_com'")
            dt_type = cursor.fetchone()
            if dt_type and dt_type[0] == 'text':
                cursor.execute("ALTER TABLE proventos_provisionados ALTER COLUMN data_com TYPE DATE USING to_date(data_com, 'DD/MM/YYYY')")
                cursor.execute("ALTER TABLE proventos_provisionados ALTER COLUMN data_pagamento TYPE DATE USING to_date(data_pagamento, 'DD/MM/YYYY')")
        except Exception as e:
            import logging
            logging.warning(f"Aviso na migração de datas do proventos_provisionados: {e}")
    
        conn.commit()

def _query_to_df(query, conn, params=None):
    """Helper para converter uma query SQL em DataFrame Pandas."""
    import pandas as pd
    cursor = conn.cursor()
    cursor.execute(query, params) if params else cursor.execute(query)
    data = cursor.fetchall()
    cols = [desc[0] for desc in cursor.description] if cursor.description else []
    return pd.DataFrame(data, columns=cols)
