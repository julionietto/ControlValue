import os
import sys

# Garante que o diretório raiz está no path para importar os módulos do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.dividends import save_provento

def main():
    # Dados fornecidos
    user_id = 1 
    ano = 2025
    mes = 5
    ticker = 'MGLU3.SA'
    valor = 244.14
    
    print(f"Inserindo provento: Ticker={ticker}, Ano={ano}, Mês={mes}, Valor={valor}, User ID={user_id}")
    
    try:
        # A função save_provento verifica se já existe e atualiza, senão insere
        save_provento(ano, mes, ticker, valor, user_id)
        print("Registro de provento recuperado e inserido com sucesso!")
    except Exception as e:
        print(f"Erro ao inserir provento: {e}")

if __name__ == "__main__":
    main()
