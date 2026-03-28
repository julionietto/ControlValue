import sqlite3

def migrate():
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    print("Adding price_ceiling and fair_value columns...")
    
    try:
        cursor.execute("ALTER TABLE assets ADD COLUMN price_ceiling REAL DEFAULT 0")
        print("Column price_ceiling added.")
    except sqlite3.OperationalError as e:
        print(f"price_ceiling: {e}")
        
    try:
        cursor.execute("ALTER TABLE assets ADD COLUMN fair_value REAL DEFAULT 0")
        print("Column fair_value added.")
    except sqlite3.OperationalError as e:
        print(f"fair_value: {e}")
        
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
