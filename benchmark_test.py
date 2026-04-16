import time
import pandas as pd
import database as db

def test_db_operations():
    user_id = 1
    
    print("Testing get_all_asset_histories...")
    t0 = time.time()
    df = db.get_all_asset_histories(user_id)
    t1 = time.time()
    print(f"get_all_asset_histories time: {t1 - t0:.4f}s - Rows: {len(df)}")
    
    print("Testing get_proventos...")
    t0 = time.time()
    df = db.get_proventos(user_id)
    t1 = time.time()
    print(f"get_proventos time: {t1 - t0:.4f}s - Rows: {len(df)}")
    
    print("Testing get_all_total_proventos...")
    t0 = time.time()
    val = db.get_all_total_proventos(user_id)
    t1 = time.time()
    print(f"get_all_total_proventos time: {t1 - t0:.4f}s - Value: {val}")

if __name__ == '__main__':
    test_db_operations()
