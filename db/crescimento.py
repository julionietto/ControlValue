import psycopg2.extras
from db.connection import get_db_connection
import pandas as pd
import streamlit as st

def clear_crescimento_cache():
    """Limpa o cache de crescimento patrimonial sem invalidar os caches de cotações/ativos."""
    try:
        get_crescimento_patrimonial.clear()
    except Exception:
        pass

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
        clear_crescimento_cache()

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
        clear_crescimento_cache()

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
        clear_crescimento_cache()

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

def sync_crescimento_patrimonial_current_year(user_id, current_saldo=None):
    """
    Garante que o registro do ano corrente exista e reflita o Saldo Atual do investidor.
    Quando um novo ano começa, o ano anterior é preservado como histórico e o novo ano
    passa a receber as atualizações contínuas do Saldo Atual.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    try:
        sp_tz = ZoneInfo("America/Sao_Paulo")
        current_year = datetime.now(sp_tz).year
    except Exception:
        current_year = datetime.now().year

    if current_saldo is None:
        try:
            import executive_report_service as exec_svc
            _, _, _, total_atual, _, _, _ = exec_svc.get_user_portfolio_data(user_id)
            current_saldo = float(total_atual)
        except Exception:
            current_saldo = 0.0

    save_crescimento_patrimonial(current_year, float(current_saldo), user_id)
    return True

def check_and_rollover_crescimento_all_users():
    """
    Executa a verificação diária de Pico Histórico e virada anual para todos os usuários cadastrados.
    Lógica de atualização:
    - Se o usuário ainda não possuir registro para o ano corrente (ex: virada de ano no dia 1º de Janeiro):
      cria o registro inicial do ano corrente e registra o saldo diário.
    - Se o usuário já possuir registro do ano: verifica se o saldo atual é MAIOR que o
      pico histórico registrado. Se for maior, atualiza para o novo recorde no registro anual e no histórico diário.
    - Se não for maior que o pico histórico: não faz nada, preservando o banco e evitando escritas desnecessárias.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import logging
    try:
        sp_tz = ZoneInfo("America/Sao_Paulo")
        current_year = datetime.now(sp_tz).year
    except Exception:
        current_year = datetime.now().year

    from db.auth import get_all_users
    users = get_all_users()
    if not users:
        return 0

    count_synced = 0
    try:
        import executive_report_service as exec_svc
    except Exception as e:
        logging.warning(f"Não foi possível carregar executive_report_service: {e}")
        return 0

    for u in users:
        uid = u['id']
        try:
            _, _, _, total_atual, _, _, _ = exec_svc.get_user_portfolio_data(uid)
            val = float(total_atual)
            if val <= 0:
                continue

            pico_atual = get_pico_historico(uid)
            rec_ano = get_crescimento_record_by_year(current_year, uid)

            # 1. Caso de virada anual / registro inexistente para o ano corrente:
            if rec_ano is None:
                save_crescimento_patrimonial(current_year, val, uid)
                record_daily_balance(uid, val)
                count_synced += 1
                logging.info(f"Crescimento anual inicializado para user {uid}: Ano {current_year} = R$ {val:,.2f}")
            # 2. Caso de novo recorde patrimonial (superou o pico histórico):
            elif val > pico_atual:
                save_crescimento_patrimonial(current_year, val, uid)
                record_daily_balance(uid, val)
                count_synced += 1
                logging.info(f"Novo pico histórico registrado para user {uid}: R$ {pico_atual:,.2f} -> R$ {val:,.2f}")
            # 3. Caso não supere o pico: não faz nada
        except Exception as e:
            logging.warning(f"Erro ao processar rollover de crescimento para user {uid}: {e}")

    if count_synced > 0:
        clear_crescimento_cache()
    return count_synced


def record_daily_balance(user_id, saldo_atual, data_ref=None):
    """
    Registra ou atualiza o saldo atual diário do investidor para histórico contínuo (Pico Histórico).
    Mantém para sempre o registro de cada dia para cada usuário.
    """
    if saldo_atual is None:
        return False
    user_id = int(user_id)
    saldo_atual = float(saldo_atual)

    if data_ref is None:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        try:
            sp_tz = ZoneInfo("America/Sao_Paulo")
            data_ref = datetime.now(sp_tz).date()
        except Exception:
            data_ref = datetime.now().date()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO historico_saldo_diario (user_id, data, saldo_atual, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, data)
            DO UPDATE SET 
                saldo_atual = GREATEST(historico_saldo_diario.saldo_atual, EXCLUDED.saldo_atual),
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, data_ref, saldo_atual)
        )
        conn.commit()
    return True


def get_pico_historico(user_id):
    """
    Busca no banco de dados o maior valor de saldo patrimonial já registrado para o user_id,
    considerando o histórico diário de saldos e os registros anuais de crescimento patrimonial.
    """
    user_id = int(user_id)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT MAX(maior_saldo) FROM (
                SELECT MAX(saldo_atual) AS maior_saldo FROM historico_saldo_diario WHERE user_id = %s
                UNION ALL
                SELECT MAX(valor_final) AS maior_saldo FROM crescimento_patrimonial WHERE user_id = %s
            ) sub
            """,
            (user_id, user_id)
        )
        row = cursor.fetchone()
        if row and row[0] is not None:
            return float(row[0])
        return 0.0

