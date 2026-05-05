import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import db
import services as svc

def run_sync():
    print("Iniciando rotina de Sincronização de Proventos Provisionados...")
    
    # 1. Verifica fuso horário
    sp_tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(sp_tz)
    today_str = now.strftime('%Y-%m-%d')
    
    print(f"Data atual (SP): {now.strftime('%Y-%m-%d %H:%M:%S')}")

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
                WHERE asset_type IN ('Ações', 'Fiis', 'ETF', 'Stocks', 'Reits')
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
        df, err, raw = svc.fetch_investidor10_proventos(tickers_with_types)
        
        if df.empty and not raw:
            # Se não retornou nada e deu erro
            print("Nenhum dado retornado ou erro no scraping.")
            db.log_sync_execution(today_str, 'ERROR', 'Falha no Scraping: Retorno vazio.')
            return

        print(f"Scraping concluído. {len(df)} proventos futuros encontrados. Consolidando na base...")

        # 5. Salva os resultados para cada usuário que possui o ativo
        affected_users = set()
        
        # Busca a cotação do dólar para conversão de Stocks e Reits
        try:
            import yfinance as yf
            data_usd = yf.Ticker("BRL=X").history(period="5d")
            usd_rate = float(data_usd['Close'].iloc[-1]) if not data_usd.empty else 5.0
        except:
            usd_rate = 5.0
            
        with db.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Para cada ativo encontrado no scraper
            for index, row in df.iterrows():
                ticker_base = row['Ativo']
                tipo = row['Tipo']
                data_com = row['Data Com']
                data_pagamento = row['Data Pagamento']
                valor = float(row['Valor'])
                
                # Aplica o desconto de IR na fonte conforme a data com (Regra 2026)
                if 'juros' in str(tipo).lower() or 'jscp' in str(tipo).lower():
                    from datetime import date
                    # Se data_com for string, converter para date (o scraper costuma retornar objetos date)
                    if isinstance(data_com, str):
                        try:
                            d_com_obj = datetime.strptime(data_com, '%d/%m/%Y').date()
                        except:
                            d_com_obj = date(2026, 1, 1) # Fallback seguro
                    else:
                        d_com_obj = data_com
                        
                    cutoff_date = date(2026, 1, 1)
                    if d_com_obj < cutoff_date:
                        valor = valor * 0.85      # 15% de IR
                    else:
                        valor = valor * 0.8252    # 17.48% de IR (Regra 2026)
                    
                ticker_sa = f"{ticker_base}.SA"
                
                # Descobre quem tem esse ativo (com ou sem .SA) e pega o ticker exato e o tipo do banco
                cursor.execute("SELECT DISTINCT ticker, user_id, asset_type FROM assets WHERE ticker IN (%s, %s)", (ticker_base, ticker_sa))
                users_with_asset = cursor.fetchall()
                
                for u in users_with_asset:
                    db_ticker = u[0]
                    user_id = u[1]
                    asset_type = u[2]
                    
                    # Converte para BRL se for ativo internacionalizado
                    user_valor = valor
                    if asset_type in ['Stocks', 'Reits']:
                        user_valor = valor * usd_rate
                        
                    # Salva (upsert) respeitando o sufixo original do banco
                    db.upsert_provento_provisionado(db_ticker, tipo, data_com, data_pagamento, user_valor, user_id)
                    affected_users.add(user_id)
                    
        # 6. Sincroniza a tabela de proventos para os usuários afetados
        print(f"Atualizando tabela de proventos para {len(affected_users)} usuários...")
        for uid in affected_users:
            db.sync_proventos_from_provisionados(uid)
        
        print("Sincronização gravada no banco de dados com sucesso!")
        db.log_sync_execution(today_str, 'SUCCESS', f"Sincronizados {len(df)} proventos para {len(tickers_with_types)} ativos.")

    except Exception as e:
        error_msg = f"Erro crítico na execução do job: {str(e)}"
        print(error_msg)
        db.log_sync_execution(today_str, 'ERROR', error_msg)

if __name__ == "__main__":
    run_sync()
