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

        # UI Initialisierung
        self.w_rechnung_hinzufuegen.hide()

        self.db_path = "rechnungsverwaltung.db"  # DB Pfad festlegen

        self.selected_ids = {}  # Dictionary für die gespeicherten IDs

        # Tabellen laden
        self.load_table(self.tv_kunden, "view_customers_full")
        self.load_table(self.tv_dienstleister, "view_service_provider_full")
        self.load_table(self.tv_rechnungen, "INVOICES")
        self.load_table(self.tv_positionen, "view_positions_full")

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

            if table_name == "view_positions_full":
                model = current.model()
                spalten_anzahl = model.columnCount()
                werte = [current.sibling(current.row(), col).data() for col in range(spalten_anzahl)]

                # Beispiel: Du musst hier die richtigen Felder aus deiner UI anpassen
                self.tb_pos.setText(str(werte[0]))  # Bezeichnung
                self.tb_pos.setEnabled(False)
                self.tb_bezeichnung.setText(str(werte[1]))  # Bezeichnung
                self.tb_bezeichnung.setEnabled(False)
                self.tb_beschreibung.setText(str(werte[2]))  # Beschreibung
                self.tb_beschreibung.setEnabled(False)
                self.dsb_flaeche.setValue(float(werte[3].replace(",", "."))) # Fläche/Menge
                self.dsb_flaeche.setEnabled(False)
                self.dsb_ppe.setValue(float(werte[4].replace(",", ".")))  # PPE Preis pro Einheit
                self.dsb_ppe.setEnabled(False)
            elif table_name == "view_service_provider_full":
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
                self.tb_iban.setText(str(werte[6]))  # IBAN
                self.tb_iban.setEnabled(False)
                self.tb_bic.setText(str(werte[7]))  # BIC
                self.tb_bic.setEnabled(False)
                self.tb_kreditinstitut.setText(str(werte[8]))  # Kreditinstitut
                self.tb_kreditinstitut.setEnabled(False)
                self.tb_dienst_strasse.setText(str(werte[9]))  # Straße
                self.tb_dienst_strasse.setEnabled(False)
                self.tb_dienst_hn.setText(str(werte[10]))  # Hausnr.
                self.tb_dienst_hn.setEnabled(False)
                self.tb_dienst_stadt.setText(str(werte[11]))  # Stadt
                self.tb_dienst_stadt.setEnabled(False)
                self.tb_dienst_plz.setText(str(werte[12]))  # PLZ
                self.tb_dienst_plz.setEnabled(False)
                self.cb_dienst_land.setCurrentText(str(werte[13]))  # Land
                self.cb_dienst_land.setEnabled(False)
                self.tb_dienst_ceo.setText(str(werte[14]))  # CEO NAme
                self.tb_dienst_ceo.setEnabled(False)

            elif table_name == "view_customers_full":
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

            elif table_name == "INVOICES":
                model = current.model()
                # Hier wird die ID der Rechnung an `load_positions` übergeben
                invoice_id = current.sibling(current.row(), 0).data()  # Annahme: die ID ist in der ersten Spalte
                self.load_positions(invoice_id)  # Positionen für diese Rechnung laden

    def load_positions(self, invoice_id):
        # Hier Positionen für die ausgewählte Rechnung laden
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.POS_ID, p.NAME, p.DESCRIPTION, p.AREA, p.UNIT_PRICE, p.CREATION_DATE
            FROM POSITIONS AS p
            JOIN INVOICES AS i ON p.FK_INVOICE_NR = i.INVOICE_NR
            WHERE i.INVOICE_NR = ?
        """, (invoice_id,))
        daten = cursor.fetchall()
        spalten = [desc[0] for desc in cursor.description]
        conn.close()

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(spalten)
        for zeile in daten:
            model.appendRow([QStandardItem(str(wert)) for wert in zeile])

        self.tv_detail_positions.setModel(model)  # Update die Detail-Positionen-Tabelle

    def load_positions_table(self):
        # Initialisierte leere Positionen-Tabelle
        self.tv_detail_positions.setModel(QStandardItemModel())  # Leere Tabelle, bis eine Rechnung ausgewählt wird

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
