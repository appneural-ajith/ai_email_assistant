import sqlite3

def get_db_connection(db_path='emails.db'):
    conn = sqlite3.connect(db_path)
    return conn

def close_db_connection(conn):
    conn.close()
