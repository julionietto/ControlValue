from db.connection import get_db_connection, _query_to_df, clear_db_cache
import pandas as pd
from datetime import datetime, date
import streamlit as st

def _parse_date_to_iso(date_val):
    if pd.isna(date_val) or date_val is None:
        return None
    if isinstance(date_val, (pd.Timestamp, datetime, date)):
        return date_val.strftime('%Y-%m-%d')
    date_str = str(date_val).strip()
    if not date_str or date_str.lower() == 'nan':
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y'):
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    try:
        return pd.to_datetime(date_str).strftime('%Y-%m-%d')
    except:
        return None

@st.cache_data(ttl=300)
def get_opcoes(user_id):
    with get_db_connection() as conn:
        df = _query_to_df("SELECT * FROM opcoes WHERE user_id = %s ORDER BY dt_vencimento ASC, ativo ASC", conn, params=(user_id,))
    return df

def insert_opcao(ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, user_id, 
                 tipo_operacao='VENDA', qtd_inicial=0, vl_opcao_inicial=0, vl_premio_inicial=0, 
                 qtd_final=0, vl_opcao_final=0, vl_premio_final=0, resultado=0):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO opcoes (ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, user_id,
                               tipo_operacao, qtd_inicial, vl_opcao_inicial, vl_premio_inicial, qtd_final, vl_opcao_final, vl_premio_final, resultado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, user_id,
              tipo_operacao, qtd_inicial, vl_opcao_inicial, vl_premio_inicial, qtd_final, vl_opcao_final, vl_premio_final, resultado))
        conn.commit()
        clear_db_cache()

def update_opcao(opcao_id, user_id, ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status,
                 tipo_operacao=None, qtd_inicial=None, vl_opcao_inicial=None, vl_premio_inicial=None, 
                 qtd_final=None, vl_opcao_final=None, vl_premio_final=None, resultado=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE opcoes 
            SET ativo=%s, strike=%s, tp_opcao=%s, dt_operacao=%s, dt_vencimento=%s, derivativo=%s, quantidade=%s, vl_opcao=%s, vl_premio=%s, status=%s,
                tipo_operacao=%s, qtd_inicial=%s, vl_opcao_inicial=%s, vl_premio_inicial=%s, 
                qtd_final=%s, vl_opcao_final=%s, vl_premio_final=%s, resultado=%s
            WHERE id=%s AND user_id=%s
        ''', (ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status,
              tipo_operacao, qtd_inicial, vl_opcao_inicial, vl_premio_inicial, qtd_final, vl_opcao_final, vl_premio_final, resultado,
              opcao_id, user_id))
        conn.commit()
        clear_db_cache()

def delete_opcao(opcao_id, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM opcoes WHERE id=%s AND user_id=%s", (opcao_id, user_id))
        conn.commit()
        clear_db_cache()

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
                    ativo = str(row.iloc[0]).strip().upper()
                    if ativo and not ativo.endswith(".SA") and "." not in ativo and "-" not in ativo:
                        ativo += ".SA"
                    strike = parse_currency(row.iloc[1])
                    tp_opcao = row.iloc[2].strip()
                    dt_operacao = _parse_date_to_iso(row.iloc[3])
                    dt_vencimento = _parse_date_to_iso(row.iloc[4])
                    if not dt_operacao or not dt_vencimento:
                        raise ValueError("Data de operação ou vencimento inválida.")

                    derivativo = row.iloc[5].strip()
                    quantidade = int(row.iloc[6])
                    vl_opcao = parse_currency(row.iloc[7])
                    vl_premio = parse_currency(row.iloc[8])
                    status = row.iloc[9].strip()
                    
                    cursor.execute('''
                        INSERT INTO opcoes (ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, user_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (ativo, strike, tp_opcao, dt_operacao, dt_vencimento, derivativo, quantidade, vl_opcao, vl_premio, status, user_id))
                except (ValueError, IndexError):
                    continue
            conn.commit()
            clear_db_cache()
        return True, "Importação de Opções concluída com sucesso."
    except Exception as e:
        return False, f"Erro ao importar Opções: {str(e)}"

def get_all_open_opcoes():
    """Busca todos os derivativos com status 'Aberta' de todos os usuários."""
    with get_db_connection() as conn:
        df = _query_to_df("SELECT id, derivativo, strike FROM opcoes WHERE status = 'Aberta'", conn)
    return df

def update_opcao_strike(opcao_id, new_strike):
    """Atualiza apenas o valor do strike de um derivativo específico."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE opcoes SET strike = %s WHERE id = %s", (new_strike, opcao_id))
        conn.commit()
        clear_db_cache()
