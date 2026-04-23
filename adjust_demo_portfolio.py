import database as db
import yfinance as yf
import pandas as pd
from contextlib import contextmanager

USER_ID = 7

REPLACEMENTS = [
    # old_ticker, new_ticker, new_type
    ('ARE', 'AAPL', 'Stocks'),
    ('NHI', 'META', 'Stocks'),
    ('NNN', 'KO', 'Stocks'),
    ('O', 'GOOG', 'Stocks'),
    ('VICI', 'NVDA', 'Stocks'),
    ('KLBN4.SA', 'KLBN11.SA', 'Ações'),
    ('BBDC3.SA', 'BBDC4.SA', 'Ações')
]

def fetch_historical_price(ticker, date_str):
    """Busca o preço de fechamento do ticker na data informada (YYYY-MM-DD)."""
    try:
        date_obj = pd.to_datetime(date_str)
        start_date = date_obj.strftime('%Y-%m-%d')
        # Busca até 5 dias a frente pra garantir que acha o pregão (fim de semana/feriado)
        end_date = (date_obj + pd.Timedelta(days=5)).strftime('%Y-%m-%d') 
        
        data = yf.download(ticker, start=start_date, end=end_date, progress=False, ignore_tz=True)
        if not data.empty and 'Close' in data:
            close_series = data['Close']
            if isinstance(close_series, pd.DataFrame):
                close_series = close_series[ticker]
            # O primeiro valor válido encontrado nessa faixa
            val = float(close_series.dropna().iloc[0])
            return val
    except Exception as e:
        print(f"Erro ao buscar preco {ticker} em {date_str}: {e}")
    return None

def merge_proventos(old_ticker, new_ticker, user_id, conn):
    cursor = conn.cursor()
    # Pega todos do antigo
    cursor.execute("SELECT id, ano, mes, valor FROM proventos WHERE ticker = %s AND user_id = %s", (old_ticker, user_id))
    old_provs = cursor.fetchall()
    
    for prov in old_provs:
        old_id, ano, mes, valor = prov
        # Verifica se ja existe no novo
        cursor.execute("SELECT id, valor FROM proventos WHERE ticker = %s AND ano = %s AND mes = %s AND user_id = %s", (new_ticker, ano, mes, user_id))
        target = cursor.fetchone()
        
        if target:
            target_id, target_valor = target
            novo_valor = target_valor + valor
            cursor.execute("UPDATE proventos SET valor = %s WHERE id = %s", (novo_valor, target_id))
            cursor.execute("DELETE FROM proventos WHERE id = %s", (old_id,))
            print(f"  [Proventos] Somado {valor} de {old_ticker} para {new_ticker} em {mes}/{ano}. Total: {novo_valor}")
        else:
            cursor.execute("UPDATE proventos SET ticker = %s WHERE id = %s", (new_ticker, old_id))
            print(f"  [Proventos] Alterado ticker de {old_ticker} para {new_ticker} em {mes}/{ano}.")

def main():
    print("Iniciando ajuste do portfolio de demonstração...")
    db.init_connection_pool()
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        for old_ticker, new_ticker, new_type in REPLACEMENTS:
            print(f"\n--- Processando {old_ticker} -> {new_ticker} ({new_type}) ---")
            
            # 1. Checa se o velho existe
            cursor.execute("SELECT id FROM assets WHERE ticker = %s AND user_id = %s", (old_ticker, USER_ID))
            old_asset = cursor.fetchone()
            if not old_asset:
                print(f"  Ativo antigo {old_ticker} nao encontrado para user_id={USER_ID}. Pulando.")
                continue
            old_id = old_asset[0]
            
            # 2. Checa se o novo existe
            cursor.execute("SELECT id FROM assets WHERE ticker = %s AND user_id = %s", (new_ticker, USER_ID))
            new_asset = cursor.fetchone()
            
            if new_asset:
                new_id = new_asset[0]
                print(f"  Ativo alvo {new_ticker} ja existe (ID: {new_id}). Fazendo merge...")
                
                # Pega historico do velho
                cursor.execute("SELECT id, date, quantity, unit_price FROM asset_history WHERE asset_id = %s", (old_id,))
                history = cursor.fetchall()
                
                for op in history:
                    op_id, date_str, qty, unit_price = op
                    # Busca preco do NOVO ticker na data original
                    novo_preco = fetch_historical_price(new_ticker, date_str)
                    if novo_preco is None:
                        print(f"    Falha ao buscar preco de {new_ticker} em {date_str}. Mantendo original.")
                        novo_preco = unit_price
                    else:
                        print(f"    {date_str}: Preco alterado de {unit_price:.2f} para {novo_preco:.2f}")
                        
                    # Reparenta a operacao para o new_id e atualiza o preco
                    cursor.execute("UPDATE asset_history SET asset_id = %s, unit_price = %s WHERE id = %s", (new_id, novo_preco, op_id))
                
                # Merge de proventos
                merge_proventos(old_ticker, new_ticker, USER_ID, conn)
                
                # Deleta o velho (primeiro deleta operations se sobrou algo? Não deveria sobrar, mas por segurança...)
                cursor.execute("DELETE FROM asset_history WHERE asset_id = %s", (old_id,))
                cursor.execute("DELETE FROM assets WHERE id = %s", (old_id,))
                print(f"  Ativo {old_ticker} (ID: {old_id}) deletado.")
                
                # Recalcula o saldo do novo
                db.recalculate_asset_balance(new_id, conn)
                
            else:
                print(f"  Ativo alvo {new_ticker} nao existe. Renomeando e atualizando historico...")
                
                # Atualiza ticker, tipo e currency
                currency = 'USD' if new_type in ['Stocks', 'Reits'] else 'BRL'
                cursor.execute("UPDATE assets SET ticker = %s, asset_type = %s, currency = %s WHERE id = %s", (new_ticker, new_type, currency, old_id))
                
                # Atualiza os precos no historico
                cursor.execute("SELECT id, date, quantity, unit_price FROM asset_history WHERE asset_id = %s", (old_id,))
                history = cursor.fetchall()
                
                for op in history:
                    op_id, date_str, qty, unit_price = op
                    novo_preco = fetch_historical_price(new_ticker, date_str)
                    if novo_preco is None:
                        print(f"    Falha ao buscar preco de {new_ticker} em {date_str}. Mantendo original.")
                        novo_preco = unit_price
                    else:
                        print(f"    {date_str}: Preco alterado de {unit_price:.2f} para {novo_preco:.2f}")
                        
                    cursor.execute("UPDATE asset_history SET unit_price = %s WHERE id = %s", (novo_preco, op_id))
                
                # Atualiza tickers na tabela de proventos
                cursor.execute("UPDATE proventos SET ticker = %s WHERE ticker = %s AND user_id = %s", (new_ticker, old_ticker, USER_ID))
                print(f"  Proventos renomeados de {old_ticker} para {new_ticker}.")
                
                # Recalcula
                db.recalculate_asset_balance(old_id, conn)
                
            conn.commit()
            print("  Concluido.")
    print("Script finalizado com sucesso!")

if __name__ == "__main__":
    main()
