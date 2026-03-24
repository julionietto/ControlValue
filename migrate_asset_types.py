import sqlite3

def migrate():
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    print("Migrating asset types...")
    
    # Migrate Ações BR to Ações
    cursor.execute("UPDATE assets SET asset_type = 'Ações' WHERE asset_type = 'Ações BR'")
    print(f"Ações BR -> Ações: {cursor.rowcount} rows updated")
    
    # Migrate FII to Fiis
    cursor.execute("UPDATE assets SET asset_type = 'Fiis' WHERE asset_type = 'FII'")
    print(f"FII -> Fiis: {cursor.rowcount} rows updated")
    
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
