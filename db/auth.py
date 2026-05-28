import bcrypt
import hashlib
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from db.connection import get_db_connection
import psycopg2.extras

# Variável global para controle da thread de desbloqueio
_unblock_thread_active = False

def _unblock_worker():
    """Worker que roda em segundo plano para limpar bloqueios expirados."""
    global _unblock_thread_active
    while True:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                sp_tz = ZoneInfo("America/Sao_Paulo")
                cursor.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE locked_until IS NOT NULL AND locked_until <= %s", (datetime.now(sp_tz).replace(tzinfo=None),))
                conn.commit()
                cursor.execute("SELECT COUNT(*) FROM users WHERE locked_until IS NOT NULL")
                count = cursor.fetchone()[0]
                
            if count == 0:
                _unblock_thread_active = False
                break
        except Exception as e:
            print(f"Erro na thread de desbloqueio: {e}")
            
        time.sleep(60)

def trigger_unblock_thread():
    """Inicia a thread de desbloqueio se ela não estiver ativa."""
    global _unblock_thread_active
    if not _unblock_thread_active:
        _unblock_thread_active = True
        thread = threading.Thread(target=_unblock_worker, daemon=True)
        thread.start()

def hash_password(password):
    """Gera um hash bcrypt para a senha."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(plain_password, hashed_password):
    """Verifica se a senha coincide com o hash atual ou legado."""
    plain_bytes = plain_password.encode()
    if hashed_password.startswith('$2b$'):
        try:
            is_valid = bcrypt.checkpw(plain_bytes, hashed_password.encode())
            return is_valid, False
        except Exception:
            return False, False
    else:
        legacy_hash = hashlib.sha256(plain_bytes).hexdigest()
        if legacy_hash == hashed_password:
            return True, True
        return False, False

def verify_user(login_identifier, password):
    """Verifica o usuário pelo email ou pelo nome 'admin'."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if login_identifier == 'admin':
            cursor.execute("SELECT id, username, password, email, birth_date, failed_attempts, locked_until, theme_preference FROM users WHERE username = %s", (login_identifier,))
        else:
            cursor.execute("SELECT id, username, password, email, birth_date, failed_attempts, locked_until, theme_preference FROM users WHERE email = %s", (login_identifier,))
        
        row = cursor.fetchone()
        if not row:
            return False, None, None, False, 'NOT_FOUND', None, None
            
        user_id, username, hashed_password, email, birth_date, failed_attempts, locked_until, theme_preference = row
        
        if locked_until:
            sp_tz = ZoneInfo("America/Sao_Paulo")
            if datetime.now(sp_tz).replace(tzinfo=None) < locked_until:
                return False, user_id, username, False, 'LOCKED', locked_until, None
            else:
                cursor.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = %s", (user_id,))
                conn.commit()
                failed_attempts = 0
                locked_until = None
        
        is_valid, needs_rehash = verify_password(password, hashed_password)
        if is_valid:
            cursor.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = %s", (user_id,))
            if needs_rehash:
                new_hash = hash_password(password)
                cursor.execute("UPDATE users SET password = %s WHERE id = %s", (new_hash, user_id))
            conn.commit()
            is_admin_flag = (username == 'admin' and (not email or email.strip() == "") and (not birth_date or birth_date.strip() == ""))
            return True, user_id, username, is_admin_flag, 'SUCCESS', None, theme_preference
        else:
            new_failed = failed_attempts + 1
            new_locked_until = None
            if new_failed >= 3:
                sp_tz = ZoneInfo("America/Sao_Paulo")
                new_locked_until = datetime.now(sp_tz).replace(tzinfo=None) + timedelta(minutes=5)
                trigger_unblock_thread()
            cursor.execute("UPDATE users SET failed_attempts = %s, locked_until = %s WHERE id = %s", (new_failed, new_locked_until, user_id))
            conn.commit()
            return False, user_id, username, False, 'WRONG_PASS', new_locked_until, None

def get_user_count():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]

def create_user(username, email, birth_date, password):
    if username.lower().strip() == 'admin':
        if get_user_count() > 0:
            raise ValueError("O nome de usuário 'admin' é reservado.")
    hashed = hash_password(password)
    sp_tz = ZoneInfo("America/Sao_Paulo")
    now_str = datetime.now(sp_tz).strftime('%Y-%m-%d %H:%M:%S')
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, birth_date, password, created_at) VALUES (%s, %s, %s, %s, %s)", (username, email, birth_date, hashed, now_str))
        conn.commit()

def get_user_by_email(email):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT id, username, email FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_all_users():
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT id, username, email, birth_date, created_at, failed_attempts, locked_until FROM users ORDER BY id ASC")
        return cursor.fetchall()

def admin_create_user(username, email, birth_date, password):
    create_user(username, email, birth_date, password)

def admin_update_user(user_id, username, email, birth_date, new_password=None):
    if username.lower().strip() == 'admin':
        email = None
        birth_date = None
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if new_password:
            hashed = hash_password(new_password)
            cursor.execute("UPDATE users SET username = %s, email = %s, birth_date = %s, password = %s WHERE id = %s", (username, email, birth_date, hashed, user_id))
        else:
            cursor.execute("UPDATE users SET username = %s, email = %s, birth_date = %s WHERE id = %s", (username, email, birth_date, user_id))
        conn.commit()

def admin_unlock_user(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = %s", (user_id,))
        conn.commit()

def get_user_details(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT id, username, email, birth_date, created_at, theme_preference FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_user_theme(user_id, theme_name):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET theme_preference = %s WHERE id = %s", (theme_name, user_id))
        conn.commit()

def update_user_profile(user_id, username, email, birth_date, password=None):
    admin_update_user(user_id, username, email, birth_date, password)

def update_user_password(user_id, new_password):
    hashed = hash_password(new_password)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, user_id))
        conn.commit()

def create_password_reset_token(user_id, token, expires_in_minutes=30):
    sp_tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(sp_tz).replace(tzinfo=None)
    expires_at = now + timedelta(minutes=expires_in_minutes)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE password_resets SET used = TRUE WHERE user_id = %s AND used = FALSE", (user_id,))
        cursor.execute("INSERT INTO password_resets (user_id, token, created_at, expires_at, used) VALUES (%s, %s, %s, %s, FALSE)", (user_id, token, now, expires_at))
        conn.commit()

def verify_password_reset_token(token):
    sp_tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(sp_tz).replace(tzinfo=None)
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM password_resets WHERE token = %s", (token,))
        row = cursor.fetchone()
        if not row: return False, None, "Token inválido ou não encontrado."
        if row['used']: return False, None, "Este link de recuperação já foi utilizado."
        if now > row['expires_at']: return False, None, "Este link de recuperação expirou."
        return True, row['user_id'], "Token válido."

def reset_password_with_token(token, new_password):
    is_valid, user_id, msg = verify_password_reset_token(token)
    if not is_valid: return False, msg
    hashed = hash_password(new_password)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = %s, failed_attempts = 0, locked_until = NULL WHERE id = %s", (hashed, user_id))
        cursor.execute("UPDATE password_resets SET used = TRUE WHERE token = %s", (token,))
        conn.commit()
    return True, "Senha redefinida com sucesso."

def admin_delete_user(user_id):
    """Remove um usuário e todos os seus dados vinculados de todas as tabelas."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 1. Histórico de Ativos
        cursor.execute("DELETE FROM asset_history WHERE asset_id IN (SELECT id FROM assets WHERE user_id = %s)", (user_id,))
        # 2. Ativos
        cursor.execute("DELETE FROM assets WHERE user_id = %s", (user_id,))
        # 3. Proventos (Recebidos e Provisionados)
        cursor.execute("DELETE FROM proventos WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM proventos_provisionados WHERE user_id = %s", (user_id,))
        # 4. Opções
        cursor.execute("DELETE FROM opcoes WHERE user_id = %s", (user_id,))
        # 5. Alocações de Ativos
        cursor.execute("DELETE FROM user_allocations WHERE user_id = %s", (user_id,))
        # 6. Resets de Senha
        cursor.execute("DELETE FROM password_resets WHERE user_id = %s", (user_id,))
        # 7. O Usuário
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
