from PyQt6.QtWidgets import QMessageBox

def show_error(self, title: str, message: str):
        """
        Displays an error message in a QMessageBox.
        """
        QMessageBox.critical(self, title, message)