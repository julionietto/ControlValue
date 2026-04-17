import sys
import os

# Adiciona o diretório atual ao path para importar o database.py
sys.path.append(os.getcwd())

import database as db

def cleanup():
    print("Iniciando limpeza de usuário...")
    try:
        with db.get_db_connection() as conn:
            cursor = conn.cursor()
            # Deletar o usuário admin@test.com
            cursor.execute("DELETE FROM users WHERE email = 'admin@test.com'")
            rows_deleted = cursor.rowcount
            print(f"Sucesso: {rows_deleted} usuário(s) removido(s) com e-mail 'admin@test.com'.")
            
            # Garantir que todos os dados orfãos desse ID específico também seriam limpos (se necessário)
            # Mas como o email é admin@test.com, deve ser um cadastro indevido.
            conn.commit()
    except Exception as e:
        print(f"Erro durante a limpeza: {e}")

if __name__ == "__main__":
    cleanup()
