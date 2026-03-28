import sqlite3

def migrate():
    print("Starting migration...")
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    tables_to_migrate = ['assets', 'proventos', 'opcoes']
    
    for table in tables_to_migrate:
        # Check if column already exists
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'user_id' not in columns:
            print(f"Adding user_id to {table}...")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
        else:
            print(f"Column user_id already exists in {table}.")
            
    conn.commit()
    conn.close()
    print("Migration finished successfully.")

if __name__ == '__main__':
    migrate()
