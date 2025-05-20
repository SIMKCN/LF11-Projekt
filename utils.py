# This file contains utility functions for the application

import traceback
from PyQt6.QtWidgets import QMessageBox, QWidget, QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit

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