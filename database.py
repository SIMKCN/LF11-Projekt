# This file provides helper functions for database interactions

import sqlite3
from config import DB_PATH

def get_connection():
    """
    Returns a new connection to the SQLite database.
    """
    return sqlite3.connect(DB_PATH)

def fetch_all(query, params=None):
    """
    Executes a query and returns all results.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        data = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
    return data, columns