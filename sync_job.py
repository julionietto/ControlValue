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

    # Limpa a tabela de proventos provisionados antes de iniciar a nova coleta (Full Sync)
    print("Limpando registros antigos de proventos provisionados...")
    db.clear_all_proventos_provisionados()

    try:
        # 3. Busca todos os ativos únicos elegíveis (da carteira ativa OU com histórico de proventos no ano)
        with db.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT ticker, asset_type 
                FROM assets 
                WHERE asset_type IN ('Ações', 'Fiis', 'ETF', 'Stocks', 'Reits')
                UNION
                SELECT DISTINCT ticker, NULL as asset_type
                FROM proventos
                WHERE ano = %s
            """, (now.year,))
            rows = cursor.fetchall()
            
        if not rows:
            print("Nenhum ativo elegível encontrado no banco. Finalizando.")
            db.log_sync_execution(today_str, 'SUCCESS', 'Nenhum ativo elegível para sincronizar.')
            return

        # Consolida para garantir que cada ticker seja buscado apenas UMA vez
        # Dicionário para garantir unicidade, priorizando o asset_type não-nulo
        unique_tickers = {}
        for r in rows:
            ticker, a_type = r[0], r[1]
            if ticker not in unique_tickers or unique_tickers[ticker] is None:
                unique_tickers[ticker] = a_type

        tickers_with_types = []
        for ticker, a_type in unique_tickers.items():
            if a_type is None:
                a_type = db.infer_asset_type(ticker)
            if a_type in ['Renda Fixa', 'Fundo CETIP']:
                continue
            tickers_with_types.append({'ticker': ticker, 'type': a_type})
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
                elif 'rend. trib.' in str(tipo).lower():
                    valor = valor * 0.775        # 22.5% de IR (Rendimento Tributado)
                    
                ticker_sa = f"{ticker_base}.SA"
                
                # Descobre quem tem esse ativo (ativos atuais OU histórico de proventos do ano corrente)
                cursor.execute("""
                    SELECT DISTINCT ticker, user_id, asset_type FROM assets WHERE ticker IN (%s, %s)
                    UNION
                    SELECT DISTINCT ticker, user_id, NULL as asset_type FROM proventos WHERE ticker IN (%s, %s) AND ano = %s
                """, (ticker_base, ticker_sa, ticker_base, ticker_sa, now.year))
                raw_users = cursor.fetchall()
                
                # Consolida usuários únicos para este ativo para evitar iterações duplicadas
                unique_users = {}
                for u_ticker, u_id, u_type in raw_users:
                    if u_id not in unique_users or unique_users[u_id]['asset_type'] is None:
                        unique_users[u_id] = {'ticker': u_ticker, 'asset_type': u_type}
                
                for user_id, u_info in unique_users.items():
                    db_ticker = u_info['ticker']
                    asset_type = u_info['asset_type']
                    
                    if asset_type is None:
                        asset_type = db.infer_asset_type(db_ticker)
                    
                    # Pula se for Renda Fixa ou Fundo CETIP (Ativos Manuais)
                    if asset_type in ['Renda Fixa', 'Fundo CETIP']:
                        continue
                    
                    # Converte para BRL se for ativo internacionalizado e aplica retenção de 30% de IR (USA)
                    user_valor = valor
                    if asset_type in ['Stocks', 'Reits']:
                        user_valor = valor * usd_rate * 0.70
                        
                    # Salva (upsert) respeitando o sufixo original do banco
                    db.upsert_provento_provisionado(db_ticker, tipo, data_com, data_pagamento, user_valor, user_id)
                    affected_users.add(user_id)
                    
        # 6. Sincroniza a tabela de proventos para os usuários afetados
        print(f"Atualizando tabela de proventos para {len(affected_users)} usuários...")
        for uid in affected_users:
            db.sync_proventos_from_provisionados(uid)
        
        print("Sincronização gravada no banco de dados com sucesso!")
        db.log_sync_execution(today_str, 'SUCCESS', f"Sincronizados {len(df)} proventos para {len(tickers_with_types)} ativos.")

        # --- NOVA ROTINA: Atualização de Strike de Derivativos ---
        print("\nIniciando atualização de strikes de derivativos abertos...")
        df_opcoes = db.get_all_open_opcoes()
        if not df_opcoes.empty:
            updates_count = 0
            for _, op in df_opcoes.iterrows():
                op_id = op['id']
                ticker = op['derivativo']
                strike_atual = float(op['strike'])
                
                print(f"Verificando {ticker} (Strike atual: R$ {strike_atual:.2f})...")
                new_strike = svc.fetch_option_strike_opcoes_net(ticker)
                
                if new_strike and abs(new_strike - strike_atual) > 0.001:
                    print(f"  [UPDATE] Strike ajustado detectado: R$ {strike_atual:.2f} -> R$ {new_strike:.2f}")
                    db.update_opcao_strike(op_id, new_strike)
                    updates_count += 1
                else:
                    print(f"  [OK] Strike sem alterações.")
                
                # Pequeno delay para evitar bloqueio por excesso de requisições
                import random
                time.sleep(random.uniform(1.0, 2.5))
            
            print(f"Finalizada atualização de strikes. {updates_count} registros alterados.")
        else:
            print("Nenhum derivativo em aberto encontrado para atualização.")

    except Exception as e:
        error_msg = f"Erro crítico na execução do job: {str(e)}"
        print(error_msg)
        db.log_sync_execution(today_str, 'ERROR', error_msg)

if __name__ == "__main__":
    run_sync()
