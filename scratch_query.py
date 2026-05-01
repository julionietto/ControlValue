import sys
sys.path.append('c:\\Projeto\\ControlValue')
import database as db

try:
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ticker, data_com, data_pagamento, valor FROM proventos_provisionados WHERE ticker IN ('EGIE3', 'KLBN11', 'PETR4', 'NHI')")
        rows = cursor.fetchall()
        print('Proventos Provisionados in DB:')
        for r in rows:
            print(r)
        if not rows:
            print('None found.')
except Exception as e:
    print('DB Error:', e)
