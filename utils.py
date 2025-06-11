# This file contains utility functions for the application
import sqlite3
import traceback

from PyQt6.QtWidgets import QMessageBox
from config import DB_PATH, IS_AUTHORIZATION_ACTIVE


def show_error(parent, title, message):
    """
    Shows a critical error message box.
    """
    QMessageBox.critical(parent, title, message)

def format_exception(e):
    """
    Returns a formatted exception string with traceback.
    """
    return f"{e}\n{traceback.format_exc()}"

def show_info(parent, title, message):
    """
    Zeigt eine Info-MessageBox an.
    :param parent: Parent-Widget (z.B. self)
    :param title: Titel des Dialogs
    :param message: Nachrichtentext
    """
    QMessageBox.information(parent, title, message)


def get_max_permission(user_id):
    """
    Gibt die höchste PERMISSION_ID des Nutzers zurück.
    Wenn IS_AUTHORIZATION_ACTIVE False ist, wird immer die maximal mögliche Rechte-ID (z.B. 9999) zurückgegeben.
    Falls der Nutzer keine Rechte hat, wird 0 zurückgegeben.
    """
    if not IS_AUTHORIZATION_ACTIVE:
        return 9999

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT MAX(PERMISSION_ID)
            FROM REF_USER_PERMISSIONS
            WHERE USER_ID = ?
        """, (user_id,))
        row = cur.fetchone()
        if row and row[0] is not None:
            return int(row[0])
        else:
            return 0