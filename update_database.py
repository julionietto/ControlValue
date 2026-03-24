import re

with open('database.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '''            password TEXT NOT NULL
        )''',
    '''            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''
)

admin_funcs = '''
def get_all_users():
    with get_db_connection() as conn:
        df = pd.read_sql_query("SELECT id, username, created_at FROM users", conn)
    return df

def admin_create_user(username, password):
    hashed = hash_password(password)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        conn.commit()

def admin_update_user(user_id, username, new_password=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if new_password:
            hashed = hash_password(new_password)
            cursor.execute("UPDATE users SET username = ?, password = ? WHERE id = ?", (username, hashed, user_id))
        else:
            cursor.execute("UPDATE users SET username = ? WHERE id = ?", (username, user_id))
        conn.commit()

def admin_delete_user(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM asset_history WHERE asset_id IN (SELECT id FROM assets WHERE user_id = ?)", (user_id,))
        cursor.execute("DELETE FROM assets WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM proventos WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM opcoes WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
'''

if 'def admin_delete_user' not in content:
    with open('database.py', 'w', encoding='utf-8') as f:
        f.write(content + '\\n' + admin_funcs)
    print("Database updated!")
else:
    print("Database already updated.")
