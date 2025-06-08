# This file contains utility functions for the application

import traceback
from PyQt6.QtWidgets import QMessageBox

from auth.user_management import user_has_permission
from config import IS_AUTHORIZATION_ACTIVE


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

def has_right(parent, user_id, permission_name):
    """
    Prüft, ob der Nutzer die gewünschte Berechtigung (z.B. 'read', 'write', 'delete') hat.
    Gibt True zurück, wenn IS_AUTHORIZATION_ACTIVE ausgeschaltet ist.
    Zeigt ggf. Fehlermeldung an.
    """
    if not IS_AUTHORIZATION_ACTIVE:
        return True
    if user_id is None:
        if parent is not None:
            QMessageBox.critical(parent, "Fehler", "Benutzerkennung nicht gesetzt!")
        return False
    try:
        allowed = user_has_permission(user_id, permission_name)
        if not allowed and parent is not None:
            QMessageBox.critical(parent, "Berechtigungsfehler", "Sie haben nicht die nötigen Rechte für diese Aktion!")
        return allowed
    except Exception as e:
        if parent is not None:
            QMessageBox.critical(parent, "Fehler bei Rechteprüfung", str(e))
        return False