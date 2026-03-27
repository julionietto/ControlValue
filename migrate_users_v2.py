import sqlite3

DB_NAME = "portfolio.db"

def migrate():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
        print("Coluna 'email' adicionada com sucesso.")
    except sqlite3.OperationalError:
        print("Coluna 'email' já existe.")
        
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN birth_date TEXT")
        print("Coluna 'birth_date' adicionada com sucesso.")
    except sqlite3.OperationalError:
        print("Coluna 'birth_date' já existe.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
