import sqlite3

try:
    conn = sqlite3.connect(r"c:\Projeto\AntiGravity\portfolio.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM assets WHERE ticker = 'MGLU3.SA'")
    conn.commit()
    conn.close()
    print("MGLU3.SA deleted successfully again.")
except Exception as e:
    print(f"Error: {e}")
