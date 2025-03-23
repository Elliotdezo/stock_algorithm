import sqlite3

def connect_db(db_name):
    """ Helper function to connect to the SQLite database """
    return sqlite3.connect(db_name)

def add_columns_to_value_infos():
    """ Add new columns to the 'properties' table """
    conn = connect_db('evaluation_fonciere.db')  # Replace with your database name
    cursor = conn.cursor()
    
    # Add new columns to the 'properties' table
    cursor.execute('''
    ALTER TABLE properties ADD COLUMN NUMBER_ORDER INTEGER;
    ''')

    conn.commit()
    conn.close()
    print("Columns added successfully.")

if __name__ == "__main__":
    add_columns_to_value_infos()