import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import os

load_dotenv()
db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url)
cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cursor.execute("SELECT * FROM assets WHERE ticker LIKE '%IRDM11%'")
assets = cursor.fetchall()
print("ASSETS:")
for a in assets:
    print(a)

cursor.execute("SELECT * FROM proventos WHERE ticker LIKE '%IRDM11%'")
proventos = cursor.fetchall()
print("PROVENTOS:")
for p in proventos:
    print(p)
