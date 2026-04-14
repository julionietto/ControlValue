import sys
sys.path.append('c:\\Projeto\\InvestControl')
import database as db

# Simula adição de ativo
try:
    print("Iniciando inserção...")
    user_id = 1 # Admin
    result = db.add_empty_asset("TESTE3", "Ações", user_id)
    print(f"Resultado add_empty_asset: {result}")
    
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assets WHERE ticker = 'TESTE3'")
        row = cursor.fetchone()
        print(f"No Banco: {row}")
except Exception as e:
    import traceback
    traceback.print_exc()
