import time
import pandas as pd
import database as db
import services as svc

def test_benchmark():
    user_id = 1  # Dummy or assume 1 exists
    
    print("Testing DB connection...")
    t0 = time.time()
    # just dummy query
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
    print(f"DB connection: {time.time() - t0:.4f}s")
    
    print("Testing YFinance fetch MXRF11.SA...")
    t0 = time.time()
    prices = svc.fetch_current_prices(['MXRF11.SA'], 0)
    print(f"YFinance fetch: {time.time() - t0:.4f}s")
    print(prices)
    
    print("Testing adding empty asset...")
    t0 = time.time()
    db.add_empty_asset("MXRF11.SA", "Fiis", user_id)
    print(f"Add asset DB: {time.time() - t0:.4f}s")

    print("Testing getting all assets...")
    t0 = time.time()
    assets = db.get_all_assets(user_id)
    print(f"Get all assets DB: {time.time() - t0:.4f}s")
    
    # find the asset we just added
    if not assets.empty:
        asset_id = assets[assets['ticker'] == 'MXRF11.SA'].iloc[0]['id']
        print(f"Testing deleting asset {asset_id}...")
        t0 = time.time()
        db.delete_asset(asset_id, user_id)
        print(f"Delete asset DB: {time.time() - t0:.4f}s")

if __name__ == '__main__':
    test_benchmark()
