import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import database as db
import services as svc

def run_sync():
    print("Iniciando rotina de Sincronização de Proventos Provisionados...")
    
    # 1. Verifica fuso horário e regras de agendamento
    sp_tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(sp_tz)
    today_str = now.strftime('%Y-%m-%d')
    
    print(f"Data atual (SP): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if now.hour < 19:
        print("Ainda não são 19:00. O mercado pode estar aberto ou os dados não foram atualizados. Abortando execução para evitar chamadas desnecessárias.")
        return

    # 2. Verifica se já rodou com sucesso hoje
    if db.check_sync_completed_today(today_str):
        print(f"A sincronização já foi concluída com sucesso hoje ({today_str}). Abortando.")
        return

    try:
        # 3. Busca todos os ativos únicos elegíveis de todos os usuários
        with db.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT ticker, asset_type 
                FROM assets 
                WHERE asset_type IN ('Ações', 'Fiis', 'Stocks', 'Reits')
            """)
            rows = cursor.fetchall()
            
        if not rows:
            print("Nenhum ativo elegível encontrado no banco. Finalizando.")
            db.log_sync_execution(today_str, 'SUCCESS', 'Nenhum ativo elegível para sincronizar.')
            return

        tickers_with_types = [{'ticker': r[0], 'type': r[1]} for r in rows]
        print(f"Encontrados {len(tickers_with_types)} ativos únicos para buscar. Iniciando Web Scraper...")

        # 4. Executa a extração (usando a função existente robusta do services.py)
        # O services.py já tem os sleeps aleatórios e curl_cffi para evitar o Cloudflare
        df, err, raw = svc.fetch_statusinvest_proventos(tickers_with_types)
        
        if df.empty and not raw:
            # Se não retornou nada e deu erro
            print("Nenhum dado retornado ou erro no scraping.")
            db.log_sync_execution(today_str, 'ERROR', 'Falha no Scraping: Retorno vazio.')
            return

        print(f"Scraping concluído. {len(df)} proventos futuros encontrados. Consolidando na base...")

        # 5. Salva os resultados para cada usuário que possui o ativo
        with db.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Para cada ativo encontrado no scraper
            for index, row in df.iterrows():
                ticker = row['Ativo']
                tipo = row['Tipo']
                data_com = row['Data Com']
                data_pagamento = row['Data Pagamento']
                valor = row['Valor']
                
                # Descobre quem tem esse ativo
                cursor.execute("SELECT DISTINCT user_id FROM assets WHERE ticker = %s", (ticker,))
                users_with_asset = cursor.fetchall()
                
                for u in users_with_asset:
                    user_id = u[0]
                    # Salva (upsert) na tabela de proventos provisionados
                    db.upsert_provento_provisionado(ticker, tipo, data_com, data_pagamento, valor, user_id)
        
        print("Sincronização gravada no banco de dados com sucesso!")
        db.log_sync_execution(today_str, 'SUCCESS', f"Sincronizados {len(df)} proventos para {len(tickers_with_types)} ativos.")

    except Exception as e:
        error_msg = f"Erro crítico na execução do job: {str(e)}"
        print(error_msg)
        db.log_sync_execution(today_str, 'ERROR', error_msg)

if __name__ == "__main__":
    run_sync()
