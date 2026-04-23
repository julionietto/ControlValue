import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import database as db

DEMO_USER_ID = 7

def main():
    print(f"--- Script de Ajuste de Dados para o Usuário Demo (ID: {DEMO_USER_ID}) ---\n")
    
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Tarefa 1: Somar TESOURO SELIC e TESOURO SELIC 2029
        print("1-) Unificando ativos 'TESOURO SELIC' e 'TESOURO SELIC 2029'...")
        cursor.execute("SELECT id, ticker, average_price FROM assets WHERE user_id = %s AND ticker IN ('TESOURO SELIC', 'TESOURO SELIC 2029')", (DEMO_USER_ID,))
        ativos_selic = cursor.fetchall()
        
        saldo_total = 0.0
        id_principal = None
        ids_para_remover = []
        
        for a_id, ticker, avg_price in ativos_selic:
            saldo_total += float(avg_price) if avg_price else 0.0
            if ticker == 'TESOURO SELIC':
                id_principal = a_id
            else:
                ids_para_remover.append(a_id)
        
        if id_principal and ids_para_remover:
            cursor.execute("UPDATE assets SET average_price = %s WHERE id = %s", (saldo_total, id_principal))
            for rm_id in ids_para_remover:
                cursor.execute("DELETE FROM assets WHERE id = %s", (rm_id,))
            print(f"   Saldo unificado no 'TESOURO SELIC': R$ {saldo_total:,.2f}")
        elif id_principal and not ids_para_remover:
            print("   'TESOURO SELIC 2029' não encontrado. Nenhuma soma necessária.")
        elif not id_principal and ids_para_remover:
            # Caso só exista o 2029, renomeamos ele para TESOURO SELIC
            cursor.execute("UPDATE assets SET ticker = 'TESOURO SELIC' WHERE id = %s", (ids_para_remover[0],))
            print(f"   Ativo 'TESOURO SELIC 2029' renomeado para 'TESOURO SELIC' com saldo R$ {saldo_total:,.2f}")
        else:
            print("   Nenhum dos ativos 'TESOURO SELIC' foi encontrado no usuário 7.")
            
        # Tarefa 2: Copiar preço teto e preço justo
        print("\n2-) Copiando Preço Teto e Preço Justo dos outros usuários...")
        cursor.execute("""
            SELECT ticker, MAX(price_ceiling), MAX(fair_value)
            FROM assets
            WHERE user_id != %s AND (price_ceiling > 0 OR fair_value > 0)
            GROUP BY ticker
        """, (DEMO_USER_ID,))
        
        referencias = cursor.fetchall()
        
        atualizados = 0
        for ticker, teto, justo in referencias:
            cursor.execute("""
                UPDATE assets 
                SET price_ceiling = %s, fair_value = %s
                WHERE user_id = %s AND ticker = %s
            """, (float(teto or 0), float(justo or 0), DEMO_USER_ID, ticker))
            
            if cursor.rowcount > 0:
                atualizados += 1
                
        print(f"   Informações de preço teto e preço justo aplicadas em {atualizados} ativos do usuário {DEMO_USER_ID}.")
        
        conn.commit()

    print("\nOperação concluída com sucesso!")

if __name__ == "__main__":
    main()
