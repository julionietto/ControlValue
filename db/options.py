from db.connection import get_db_connection, _query_to_df
import pandas as pd

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

def get_opcoes_import(arquivo, user_id):
    try:
        df = pd.read_csv(arquivo)
        required_cols = ['Ativo', 'Strike', 'Tipo', 'DtOperação', 'DtVencimento', 'Derivativo', 'Quantidade', 'ValorOpção', 'ValorPrêmio', 'Status']
        if not all(col in df.columns for col in required_cols):
            return False, "Arquivo CSV não possui as colunas necessárias."
        
        from utils.formatters import parse_currency
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                try:
                    ativo = str(row[0]).strip().upper()
                    strike = parse_currency(row[1])
                    tp_opcao = row[2].strip()
                    dt_operacao = row[3].strip()
                    dt_vencimento = row[4].strip()
                    derivativo = row[5].strip()
                    quantidade = int(row[6])
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
