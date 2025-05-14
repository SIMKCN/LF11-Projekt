from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtWidgets import QMainWindow, QApplication, QTableView, QHeaderView, QLineEdit, QLabel, QMessageBox, \
    QComboBox, QDoubleSpinBox, QPlainTextEdit, QTextBrowser, QTextEdit, QPushButton
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6 import uic
import sqlite3
import sys
import traceback

"""
TODO: Abhängigkeiten einfügen
 """

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())