from PyQt6.QtCore import QTimer, QModelIndex, Qt
from PyQt6.QtWidgets import QMainWindow, QApplication, QTableView, QAbstractItemView, QHeaderView, QLabel
from PyQt6 import uic
from PyQt6.QtGui import QStandardItemModel, QStandardItem
import sqlite3
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("./Qt/main.ui", self)  # UI laden

        # UI Initialisierung
        self.w_rechnung_hinzufuegen.hide()

        self.db_path = "rechnungsverwaltung.db"  # DB Pfad festlegen

        self.selected_ids = {}  # Dictionary für die gespeicherten IDs

        # Label für das Erstellungsdatum
        self.lbl_creation_date = self.findChild(QLabel, "lbl_creation_date")

        # Tabellen laden
        self.load_table(self.tv_kunden, "view_customers_full")
        self.load_table(self.tv_dienstleister, "view_service_provider_full")
        self.load_table(self.tv_rechnungen, "view_invoices_full")
        self.load_table(self.tv_positionen, "view_positions_full")

    def load_table(self, table_view: QTableView, table_name: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {table_name}")
                data = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
        except sqlite3.Error as e:
            print(f"Datenbankfehler: {e}")
            return

        try:
            # Modell für die Tabelle erstellen
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(columns)
            for row in data:
                row_items = [QStandardItem(str(cell)) for cell in row]
                for item in row_items:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                model.appendRow(row_items)

            table_view.setModel(model)
            table_view.resizeColumnsToContents()
            table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

            header = table_view.horizontalHeader()
            for col in range(header.count()):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)

            selection_model = table_view.selectionModel()
            selection_model.currentChanged.connect(
                lambda current, previous: self.on_current_changed(current, table_name))
        except Exception as e:
            print(f"Fehler beim Setzen der Tabelle: {e}")

    def on_current_changed(self, current: QModelIndex, table_name: str):
        if current.isValid():
            # ID aus der ersten Spalte der aktuellen Zeile holen
            id_wert = current.sibling(current.row(), 0).data()
            print(f"Ausgewählte ID für '{table_name}': {id_wert}")
            self.selected_ids[table_name] = id_wert  # Speichere die ID im Dictionary

            # Erstellungsdatum basierend auf dem Table-Namen aktualisieren
            self.update_creation_date(table_name, id_wert)

            if table_name == "view_positions_full":
                self.load_position_details(current)

            elif table_name == "view_service_provider_full":
                self.load_service_provider_details(current, id_wert)

            elif table_name == "view_customers_full":
                self.load_customer_details(current)

            elif table_name == "view_invoices_full":
                self.load_positions(id_wert)

    def load_position_details(self, current: QModelIndex):
        model = current.model()
        spalten_anzahl = model.columnCount()
        werte = [current.sibling(current.row(), col).data() for col in range(spalten_anzahl)]

        self.tb_pos.setText(str(werte[0]))  # Bezeichnung
        self.tb_pos.setEnabled(False)
        self.tb_bezeichnung.setText(str(werte[1]))  # Bezeichnung
        self.tb_bezeichnung.setEnabled(False)
        self.tb_beschreibung.setText(str(werte[2]))  # Beschreibung
        self.tb_beschreibung.setEnabled(False)
        self.dsb_flaeche.setValue(float(werte[3].replace(",", ".")))  # Fläche/Menge
        self.dsb_flaeche.setEnabled(False)
        self.dsb_ppe.setValue(float(werte[4].replace(",", ".")))  # PPE Preis pro Einheit
        self.dsb_ppe.setEnabled(False)

    def load_service_provider_details(self, current: QModelIndex, id_wert):
        model = current.model()
        spalten_anzahl = model.columnCount()
        werte = [current.sibling(current.row(), col).data() for col in range(spalten_anzahl)]

        self.tb_ustidnr.setText(str(werte[0]))  # USt - IdNr.
        self.tb_ustidnr.setEnabled(False)
        self.tb_unternehmen.setText(str(werte[1]))  # Firma
        self.tb_unternehmen.setEnabled(False)
        self.tb_dienst_tel.setText(str(werte[2]))  # Telefon
        self.tb_dienst_tel.setEnabled(False)
        self.tb_dienst_mob.setText(str(werte[3]))  # Mobiltel.nr.
        self.tb_dienst_mob.setEnabled(False)
        self.tb_dienst_fax.setText(str(werte[4]))  # Fax
        self.tb_dienst_fax.setEnabled(False)
        self.tb_dienst_email.setText(str(werte[5]))  # E-Mail
        self.tb_dienst_email.setEnabled(False)
        self.tb_dienst_webseite.setText(str(werte[6]))  # E-Mail
        self.tb_dienst_webseite.setEnabled(False)
        self.tb_dienst_strasse.setText(str(werte[7]))  # Straße
        self.tb_dienst_strasse.setEnabled(False)
        self.tb_dienst_hn.setText(str(werte[8]))  # Hausnr.
        self.tb_dienst_hn.setEnabled(False)
        self.tb_dienst_stadt.setText(str(werte[9]))  # Stadt
        self.tb_dienst_stadt.setEnabled(False)
        self.tb_dienst_plz.setText(str(werte[10]))  # PLZ
        self.tb_dienst_plz.setEnabled(False)
        self.cb_dienst_land.setCurrentText(str(werte[11]))  # Land
        self.cb_dienst_land.setEnabled(False)

        # Jetzt holen wir die Geschäftsführer und Bankverbindung des Dienstleisters
        self.load_ceo_and_bank_data(id_wert)  # UST_IDNR des Dienstleisters als Argument

    def load_customer_details(self, current: QModelIndex):
        model = current.model()
        spalten_anzahl = model.columnCount()
        werte = [current.sibling(current.row(), col).data() for col in range(spalten_anzahl)]

        self.tb_vorname.setText(str(werte[1]))  # Vorname
        self.tb_vorname.setEnabled(False)
        self.tb_nachname.setText(str(werte[2]))  # Nachname
        self.tb_nachname.setEnabled(False)
        self.cb_geschlecht.setCurrentText(str(werte[3]))  # Geschlecht für Anrede in Rechnung
        self.cb_geschlecht.setEnabled(False)
        self.tb_kdnr.setText(str(werte[0]))  # Kundennummer
        self.tb_kdnr.setEnabled(False)
        self.tb_kd_strasse.setText(str(werte[4]))  # Straße
        self.tb_kd_strasse.setEnabled(False)
        self.tb_kd_hn.setText(str(werte[5]))  # Hausnummer
        self.tb_kd_hn.setEnabled(False)
        self.tb_kd_plz.setText(str(werte[6]))  # PLZ
        self.tb_kd_plz.setEnabled(False)
        self.tb_kd_stadt.setText(str(werte[7]))  # Stadt
        self.tb_kd_stadt.setEnabled(False)
        self.cb_kd_land.setCurrentText(str(werte[8]))  # Land
        self.cb_kd_land.setEnabled(False)

    def load_positions(self, invoice_id):
        # Hier Positionen für die ausgewählte Rechnung laden
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT p.POS_ID, p.NAME, p.DESCRIPTION, p.AREA, p.UNIT_PRICE, p.CREATION_DATE
                    FROM POSITIONS AS p
                    JOIN INVOICES AS i ON p.FK_INVOICE_NR = i.INVOICE_NR
                    WHERE i.INVOICE_NR = ?
                """, (invoice_id,))
                daten = cursor.fetchall()
                spalten = [desc[0] for desc in cursor.description]
        except sqlite3.Error as e:
            print(f"Datenbankfehler beim Laden der Positionen: {e}")
            return

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(spalten)
        for zeile in daten:
            row_items = []
            for wert in zeile:
                item = QStandardItem(str(wert))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Zelle nicht bearbeitbar
                row_items.append(item)
            model.appendRow(row_items)

        self.tv_positionen.setModel(model)

    def update_creation_date(self, table_name: str, id_value: str):
        # Die Logik zur Aktualisierung des Erstellungsdatums basierend auf dem Tabellennamen
        pass

# Hauptprogramm
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
