from PyQt6.QtCore import QTimer, QModelIndex
from PyQt6.QtWidgets import QMainWindow, QApplication, QTableView, QAbstractItemView
from PyQt6 import uic
from PyQt6.QtGui import QStandardItemModel, QStandardItem
import sqlite3
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("./Qt/main.ui", self)  # UI laden

        #UI Initialisierung
        self.w_rechnung_hinzufuegen.hide()

        self.db_path = "rechnungsverwaltung.db" # DB Pfad festlegen

        self.selected_ids = {}  # Dictionary für die gespeicherten IDs

        # Tabellen laden
        self.load_table(self.tv_kunden, "view_customers_full")
        self.load_table(self.tv_dienstleister, "view_service_provider_full")
        self.load_table(self.tv_rechnungen, "INVOICES")
        self.load_table(self.tv_positionen, "POSITIONS")

    def load_table(self, table_view: QTableView, table_name: str):
        try:
            # Daten aus der Datenbank laden
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {table_name}")
                daten = cursor.fetchall()
                spalten = [desc[0] for desc in cursor.description]

        except sqlite3.Error as e:
            print(f"Datenbankfehler: {e}")
            return

        # Modell für die Tabelle erstellen
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(spalten)
        for zeile in daten:
            model.appendRow([QStandardItem(str(wert)) for wert in zeile])

        # Setze das Modell für die TableView
        table_view.setModel(model)
        table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # Signal verbinden
        selection_model = table_view.selectionModel()
        selection_model.currentChanged.connect(lambda current, previous: self.on_current_changed(current, table_name))

    def on_current_changed(self, current: QModelIndex, table_name: str):
        if current.isValid():
            # ID aus der ersten Spalte der aktuellen Zeile holen
            id_wert = current.sibling(current.row(), 0).data()
            print(f"Ausgewählte ID für '{table_name}': {id_wert}")
            self.selected_ids[table_name] = id_wert  # Speichere die ID im Dictionary


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
