import psycopg2.extras
from db.connection import get_db_connection

def save_sync_log(sync_date, status, details):
    """Salva um log de execução do job de sincronização."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sync_logs (sync_date, status, details) VALUES (%s, %s, %s)",
            (sync_date, status, details)
        )
        conn.commit()

def get_last_sync_log():
    """Retorna o último log de sincronização bem-sucedido."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM sync_logs ORDER BY execution_time DESC LIMIT 1")
        return cursor.fetchone()

def check_sync_today(sync_date):
    """Verifica se já houve uma sincronização de sucesso no dia."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM sync_logs WHERE sync_date = %s AND status = 'SUCCESS'", (sync_date,))
        return cursor.fetchone() is not None

# Aliases para compatibilidade com o antigo 'database.py' e 'sync_job.py'
check_sync_completed_today = check_sync_today
log_sync_execution = save_sync_log
