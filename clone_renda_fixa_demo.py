import os
import sys

# Adiciona o diretório atual ao path para poder importar o modulo database
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import database as db

DEMO_USER_ID = 7

def main():
    print(f"--- Script de Clonagem de Renda Fixa para o Usuário Demo (ID: {DEMO_USER_ID}) ---\n")
    
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Buscar todos os ativos de Renda Fixa dos outros usuários e sumarizar o saldo
        query = """
            SELECT ticker, SUM(average_price) as saldo_total
            FROM assets 
            WHERE asset_type = 'Renda Fixa' AND user_id != %s
            GROUP BY ticker
            ORDER BY ticker
        """
        cursor.execute(query, (DEMO_USER_ID,))
        resultados = cursor.fetchall()
        
    if not resultados:
        print("Não foram encontrados ativos de Renda Fixa nos outros usuários.")
        return
        
    print("Saldos sumarizados de Renda Fixa encontrados:")
    print("-" * 60)
    print(f"{'TICKER'.ljust(30)} | {'SALDO SUMARIZADO'}")
    print("-" * 60)
    
    for ticker, saldo in resultados:
        print(f"{ticker.ljust(30)} | R$ {saldo:,.2f}")
    
    print("-" * 60)
    
    # 2. Pedir aprovação do usuário para prosseguir
    resposta = input(f"\nDeseja registrar estes saldos para o usuário Demo (ID: {DEMO_USER_ID})? (s/n): ")
    
    if resposta.lower() not in ['s', 'sim', 'y', 'yes']:
        print("Operação cancelada pelo usuário. Nenhuma alteração foi feita no banco de dados.")
        return
        
    print("\nIniciando a migração...")
    
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            # 3. Remover os ativos de Renda Fixa antigos do user_id 7 para evitar duplicidade ou lixo
            cursor.execute("DELETE FROM assets WHERE asset_type = 'Renda Fixa' AND user_id = %s", (DEMO_USER_ID,))
            
            # 4. Inserir os novos saldos sumarizados
            for ticker, saldo in resultados:
                cursor.execute("""
                    INSERT INTO assets (ticker, asset_type, quantity, average_price, user_id, currency)
                    VALUES (%s, 'Renda Fixa', 1, %s, %s, 'BRL')
                """, (ticker, float(saldo), DEMO_USER_ID))
                
            conn.commit()
            print(f"Sucesso: {len(resultados)} ativos de Renda Fixa registrados para o usuário {DEMO_USER_ID}!")
        except Exception as e:
            conn.rollback()
            print(f"Erro ao tentar migrar os dados: {e}")

if __name__ == "__main__":
    main()
