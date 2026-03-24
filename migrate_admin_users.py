import sqlite3
from database import hash_password

def migrate_admin():
    print("Starting admin migration...")
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    # 1. Add created_at
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'created_at' not in columns:
        print("Adding created_at to users...")
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT '2024-01-01 00:00:00'")
    else:
        print("Column created_at already exists in users.")
        
    # 2. Add 'admin' user if not exists
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    res = cursor.fetchone()
    if not res:
        print("Creating default admin user...")
        hashed = hash_password('admin')
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', hashed))
    else:
        print("Admin user already exists.")
        
    conn.commit()
    conn.close()
    print("Migration finished successfully.")

if __name__ == '__main__':
    migrate_admin()
