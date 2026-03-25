import database as db
import io

# Mock file-like object
csv_content = """Ano,Ticker,Jan,Fev,Mar,Abr,Mai,Jun,Jul,Ago,Set,Out,Nov,Dez
2025,ITSA4,,,132.45,,,,,,,54.01"""
file_mock = io.StringIO(csv_content)

user_id = 3 # admin
success, msg = db.import_proventos_csv(file_mock, user_id)
print(f"Success: {success}")
print(f"Message: {msg}")

# Check data
with db.get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM proventos WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    print(f"Rows found for user 3: {len(rows)}")
    for row in rows:
        print(row)
