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

def get_tab_input_data(tab_widget: QWidget):
    """
    Sammelt alle Eingabedaten eines Tabs.
    Nimmt als Key alles nach dem zweiten Unterstrich im Objektname.
    """
    data = {}
    widget_types = [QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit]
    for wtype in widget_types:
        for child in tab_widget.findChildren(wtype):
            obj_name = child.objectName()
            if not obj_name:
                continue
            parts = obj_name.split("_", 2)
            if len(parts) < 3:
                continue
            col_name = parts[2]  # alles nach dem zweiten "_"
            if isinstance(child, QLineEdit):
                data[col_name] = child.text()
            elif isinstance(child, QComboBox):
                data[col_name] = child.currentText()
            elif isinstance(child, QDoubleSpinBox):
                data[col_name] = child.value()
            elif isinstance(child, (QTextEdit, QPlainTextEdit)):
                data[col_name] = child.toPlainText()
    return data