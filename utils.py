# This file contains utility functions for the application

import traceback
from PyQt6.QtWidgets import QMessageBox

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