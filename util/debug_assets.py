import sqlite3
import pandas as pd

def debug():
    conn = sqlite3.connect('portfolio.db')
    df = pd.read_sql_query("SELECT * FROM assets", conn)
    print("Unique Asset Types in DB:")
    print(df['asset_type'].unique())
    print("\nQuantity sum by asset_type:")
    print(df.groupby('asset_type')['quantity'].sum())
    
    tipos_acoes = ['Ações', 'Fiis', 'Stocks', 'Reits']
    # Add 'Ações' if it's there
    print("\n--- Diagnostic ---")
    current_calculation_types = ['Ações', 'Fiis', 'Stocks', 'Reits']
    print(f"Current code types: {current_calculation_types}")
    print(f"Total with current types: {df[df['asset_type'].isin(current_calculation_types)]['quantity'].sum()}")
    
    proposed_types = ['Ações', 'Fiis', 'Stocks', 'Reits']
    print(f"Proposed types: {proposed_types}")
    print(f"Total with proposed types: {df[df['asset_type'].isin(proposed_types)]['quantity'].sum()}")
    
    conn.close()

if __name__ == "__main__":
    debug()
