import sqlite3

def set_dates():
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET created_at = '2026-03-22 00:00:00' WHERE username = 'admin'")
    cursor.execute("UPDATE users SET created_at = '2026-03-03 00:00:00' WHERE username = 'julionietto'")
    conn.commit()
    conn.close()
    print("Dates updated!")

if __name__ == '__main__':
    set_dates()
