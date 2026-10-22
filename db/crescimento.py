import psycopg2.extras
from db.connection import get_db_connection, clear_db_cache
import pandas as pd
import streamlit as st

@st.cache_data(ttl=300)
def get_crescimento_patrimonial(user_id):
    """
    Retorna o histórico de valor patrimonial alcançado pelo investidor ao longo dos anos,
    ordenado do ano mais recente primeiro (ano DESC).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            """
            SELECT id, user_id, ano, valor_final, created_at, updated_at
            FROM crescimento_patrimonial
            WHERE user_id = %s
            ORDER BY ano DESC
            """,
            (user_id,)
        )
        rows = cursor.fetchall()
        return pd.DataFrame(rows)

def save_crescimento_patrimonial(ano, valor_final, user_id):
    """
    Insere ou atualiza o registro de valor patrimonial para um determinado ano e usuário (Upsert).
    """
    ano = int(ano)
    valor_final = float(valor_final)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO crescimento_patrimonial (user_id, ano, valor_final, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, ano)
            DO UPDATE SET valor_final = EXCLUDED.valor_final, updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, ano, valor_final)
        )
        conn.commit()
        clear_db_cache()

def update_crescimento_patrimonial(record_id, ano, valor_final, user_id):
    """
    Atualiza um registro específico de crescimento patrimonial pelo ID e user_id.
    """
    record_id = int(record_id)
    ano = int(ano)
    valor_final = float(valor_final)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE crescimento_patrimonial
            SET ano = %s, valor_final = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
            """,
            (ano, valor_final, record_id, user_id)
        )
        conn.commit()
        clear_db_cache()

def delete_crescimento_patrimonial(record_id, user_id):
    """
    Exclui um registro de crescimento patrimonial pelo ID e user_id.
    """
    record_id = int(record_id)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM crescimento_patrimonial WHERE id = %s AND user_id = %s",
            (record_id, user_id)
        )
        conn.commit()
        clear_db_cache()

def get_crescimento_record_by_year(ano, user_id):
    """
    Busca um registro específico de crescimento patrimonial pelo ano e user_id.
    """
    ano = int(ano)
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            "SELECT id, user_id, ano, valor_final FROM crescimento_patrimonial WHERE ano = %s AND user_id = %s",
            (ano, user_id)
        )
        return cursor.fetchone()
