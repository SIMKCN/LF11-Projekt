# This file provides helper functions for database interactions

import sqlite3
from config import DB_PATH
from utils import show_error

MAX_INVOICE_CUSTOMER_ID = 100000
MAX_SERVICE_PROVIDER_ID = 1000000000

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


def get_next_primary_key(self, table_name, pk_column, pk_type):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(f"SELECT {pk_column} FROM {table_name}")
        ids = [row[0] for row in cur.fetchall()]

        if pk_type in ("invoice", "customer"):
            used_numbers = set()
            for id_str in ids:
                try:
                    num = int(str(id_str))
                    used_numbers.add(num)
                except Exception:
                    continue
            for candidate in range(1, MAX_INVOICE_CUSTOMER_ID):
                if candidate not in used_numbers:
                    return f"{candidate:05d}"
            return "99999"  # fallback

        elif pk_type == "service_provider":
            used_numbers = set()
            for id_str in ids:
                if isinstance(id_str, str) and id_str.startswith("DE") and len(id_str) == 11:
                    try:
                        num = int(id_str[2:])
                        used_numbers.add(num)
                    except Exception:
                        continue
            for candidate in range(1, MAX_SERVICE_PROVIDER_ID):
                if candidate not in used_numbers:
                    return f"DE{candidate:09d}"
            return "DE999999999"  # fallback

        elif pk_type == "positions":
            max_value = 0
            for val in ids:
                try:
                    num = int(val)
                    if num > max_value:
                        max_value = num
                except Exception:
                    continue
            return max_value + 1

        else:
            # Default: gib leeren String zurück für unbekannte Typen
            return ""

    except Exception as e:
        print(f"Fehler beim Ermitteln des nächsten Primary Keys: {e}")
        if pk_type == "service_provider":
            return "DE000000001"
        elif pk_type in ("invoice", "customer"):
            return "00001"
        elif pk_type == "positions":
            return 1
        else:
            return ""
    finally:
        try:
            conn.close()
        except Exception:
            pass