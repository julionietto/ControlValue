import os
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine
import database as db

# 1. Obter URLs
LOCAL_DB_URL = "postgresql://postgres:Magnum%405200@127.0.0.1:5432/investcontrol"

load_dotenv(override=True)
CLOUD_DB_URL = os.getenv("DATABASE_URL")

if not CLOUD_DB_URL or CLOUD_DB_URL == LOCAL_DB_URL:
    print("ERRO: A URL da nuvem no .env não foi encontrada ou continua igual à local.")
    exit(1)

print(f"URL Local: {LOCAL_DB_URL.replace('Magnum%405200', '***')}")
print(f"URL Nuvem: {CLOUD_DB_URL[:40]}...")

try:
    # 2. Inicializar tabelas na Nuvem usando a rotina do app
    print("\nInicializando tabelas na nuvem...")
    db.init_db()  # Usa o ambiente atual (Cloud via .env carregado)
    
    # Cria engines SQLAlchemy para transferência (pandas.to_sql)
    engine_local = create_engine(LOCAL_DB_URL)
    engine_cloud = create_engine(CLOUD_DB_URL.replace("postgres://", "postgresql://")) # SQLAlchemy precisa de 'postgresql://'

    tabelas = ['users', 'assets', 'asset_history', 'proventos', 'opcoes']

    for tabela in tabelas:
        print(f"\nMigrando tabela: {tabela}...")
        
        # Lê da máquina local
        df = pd.read_sql_table(tabela, con=engine_local)
        print(f"Localizados {len(df)} registros para '{tabela}'.")
        
        if len(df) > 0:
            # Apaga dados existentes na nuvem (evitar duplicação), cascateando dependências se for assets
            with engine_cloud.connect() as conn:
                try:
                    conn.execute(f"TRUNCATE TABLE {tabela} CASCADE")
                    print(f"Tabela '{tabela}' da nuvem feita a limpeza (Truncate).")
                except Exception as e:
                    print(f"Aviso ao dar Truncate: {e}")

            # Transfere para a nuvem
            # Nota: O index=False é crucial. E usaremos .to_sql com append e sem índice
            df.to_sql(tabela, con=engine_cloud, if_exists='append', index=False)
            print(f"Tabela '{tabela}' migrada com sucesso!")
        else:
            print(f"Tabela '{tabela}' ignorada (vazia).")

    print("\n✅ MUDANÇA CONCLUÍDA! Todos os dados estão seguros na nuvem.")
    
except Exception as e:
    import traceback
    traceback.print_exc()
