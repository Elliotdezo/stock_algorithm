import sqlite3


#####ADD COLUMN#####

def connect_db(db_name):
    """ Helper function to connect to the SQLite database """
    return sqlite3.connect(db_name)

def add_columns_to_value_infos():
    """ Add new columns to the 'equity_curve' table """
    conn = connect_db('stock_datas')  # Replace with your database name
    cursor = conn.cursor()
    
    # Add new columns to the 'equity_curve' table
    cursor.execute('''
    ALTER TABLE equity_curve ADD COLUMN NUMBER_ORDER INTEGER;
    ''')

    conn.commit()
    conn.close()
    print("Columns added successfully.")

if __name__ == "__main__":
    add_columns_to_value_infos()


########CLEAR DATA############

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