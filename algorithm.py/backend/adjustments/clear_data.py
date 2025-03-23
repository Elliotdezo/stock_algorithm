import sqlite3

DB_PATH = "stock_datas.db"
TABLE_NAME = "equity_curve"

def clear_backtest_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f"DELETE FROM {TABLE_NAME}")
    conn.commit()
    conn.close()

    print(f"✅ Table '{TABLE_NAME}' has been cleared.")

if __name__ == "__main__":
    clear_backtest_table()