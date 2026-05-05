import psycopg2
from db.connection import get_db_connection

with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'asset_history'")
    print("asset_history columns:")
    for row in cursor.fetchall():
        print(row)
    
    cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'proventos_provisionados'")
    print("\nproventos_provisionados columns:")
    for row in cursor.fetchall():
        print(row)
