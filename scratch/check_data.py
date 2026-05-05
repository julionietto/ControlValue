import psycopg2
from db.connection import get_db_connection

with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT date FROM asset_history LIMIT 5")
    print("asset_history dates:")
    for row in cursor.fetchall():
        print(f"'{row[0]}' (type: {type(row[0])})")
