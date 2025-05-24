# This file contains the MainWindow class for the application
import sqlite3

from PyQt6.QtWidgets import QMainWindow, QTableView, QHeaderView, QLineEdit, QLabel, QMessageBox, QComboBox, \
    QDoubleSpinBox, QPlainTextEdit, QTextBrowser, QTextEdit, QPushButton, QAbstractItemView, QWidget, QDateEdit, \
    QDialog, QFormLayout, QListWidget, QFileDialog
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6 import uic
from datetime import date
import sys
from database import get_next_primary_key
from config import UI_PATH, DB_PATH, POSITION_DIALOG_PATH
from utils import show_error, format_exception, show_info
from database import fetch_all
from logic import get_ceos_for_service_provider_form, get_service_provider_ceos, get_invoice_positions


class FileUploader(QWidget):
    def __init__(self):
        super().__init__()

        self.browseButton = QPushButton("Durchsuchen")
        self.uploadButton = QPushButton("Hochladen")
        self.fileListWidget = QListWidget()

        layout = QVBoxLayout()
        layout.addWidget(self.browseButton)
        layout.addWidget(self.uploadButton)
        layout.addWidget(self.fileListWidget)
        self.setLayout(layout)

        self.selected_files = []

        self.browseButton.clicked.connect(self.browse_files)
        self.uploadButton.clicked.connect(self.handle_upload)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Logo auswählen")
        if files:
            self.selected_files = files
            self.fileListWidget.clear()
            self.fileListWidget.addItems(files)

    def handle_upload(self):
        if not self.selected_files:
            print("Kein Logo ausgewählt")
            return
        print(f"Hochgeladen: {self.selected_files[0]}")



class CEOStNrDialog(QDialog):
    def __init__(self, ceo_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Steuernummern der Geschäftsführer")
        self.ceo_fields = {}
        layout = QFormLayout()
        for ceo in ceo_names:
            field = QLineEdit()
            layout.addRow(f"{ceo} - Steuernummer:", field)
            self.ceo_fields[ceo] = field
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok)
        self.setLayout(layout)

    def get_ceo_st_numbers(self):
        return {ceo: field.text().strip() for ceo, field in self.ceo_fields.items()}

class PositionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(POSITION_DIALOG_PATH, self)

    def get_data(self):
        # Beispiel: Passe Feldnamen an die Namen im UI an
        return {
            "NAME": self.le_name.text(),  # z.B. QLineEdit mit objectName 'le_name'
            "DESCRIPTION": self.te_description.toPlainText(),  # QTextEdit
            "AREA": self.sb_area.value(),  # QDoubleSpinBox
            "UNIT_PRICE": self.sb_unit_price.value(),  # QDoubleSpinBox
        }

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            uic.loadUi(UI_PATH, self)
        except Exception as e:
            show_error(self, "UI Loading Error", f"Could not load UI file.\nError: {str(e)}")
            sys.exit(1)

        # Mapping table views to database views
        self.table_mapping = {
            "tv_rechnungen": "view_invoices_full",
            "tv_dienstleister": "view_service_provider_full",
            "tv_kunden": "view_customers_full",
            "tv_positionen": "view_positions_full",
        }

        # Mapping for detail views
        self.detail_mapping = {
            "tv_rechnungen": self.tv_detail_rechnungen,
            "tv_dienstleister": self.tv_detail_dienstleister,
        }

        # Mapping for PK column
        self.pk_field_config = {
            "tab_rechnungen": {"field": "tb_rechnungsnummer", "table": "INVOICES", "pk_col": "INVOICE_NR", "type": "invoice"},
            "tab_kunden": {"field": "tv_kunden_Kundennummer", "table": "CUSTOMERS", "pk_col": "CUSTID", "type": "customer"},
            "tab_dienstleister": {"field": "tv_dienstleister_UStIdNr", "table": "SERVICE_PROVIDER", "pk_col": "UST_IDNR", "type": "service_provider"},
            "tab_positionen": {"field": "tv_positionen_PositionsID", "table": "POSITIONS", "pk_col": "POS_ID", "type": "positions"}
        }

        # Mapping for Search Label
        self.tab_search_label_text = {
            "tab_rechnungen": "Rechnungen durchsuchen",
            "tab_dienstleister": "Dienstleister durchsuchen",
            "tab_kunden": "Kunden durchsuchen",
            "tab_positionen": "Positionen durchsuchen"
        }

        self.tab_field_mapping = {
            # Achtung: Feldnamen müssen zu den UI-Feldnamen passen!
            "tab_kunden": [
                "tv_kunden_Kundennummer", "tv_kunden_Vorname", "tv_kunden_Nachname", "tv_kunden_Geschlecht"
            ],
            "tab_kunden_address": [
                "tv_kunden_Strasse", "tv_kunden_Hausnummer", "tv_kunden_Stadt", "tv_kunden_PLZ", "tv_kunden_Land"
            ],
            "tab_dienstleister": [
                "tv_dienstleister_UStIdNr", "tv_dienstleister_Unternehmensname", "tv_dienstleister_Email",
                "tv_dienstleister_Telefonnummer", "tv_dienstleister_Mobiltelefonnummer", "tv_dienstleister_Faxnummer",
                "tv_dienstleister_Webseite", "tv_dienstleister_CEOS"
            ],
            "tab_dienstleister_address": [
                "tv_dienstleister_Strasse", "tv_dienstleister_Hausnummer", "tv_dienstleister_Stadt", "tv_dienstleister_PLZ", "tv_dienstleister_Land",
            ],
            # Konten/BANK werden ggf. als Listeneintrag oder dynamische Felder erfasst
            "tab_rechnungen": [
                "tb_rechnungsnummer", "de_erstellungsdatum", "dsb_lohnkosten", "dsb_mwst_lohnkosten", "dsb_mwst_positionen"
            ],
            "tab_rechnungen_fk": [  # Foreign Keys für Relationen
                "fk_custid", "fk_ust_idnr"
            ],
            "tab_positionen": [
                "tv_positionen_PositionsID", "tv_positionen_Bezeichnung", "tv_positionen_Beschreibung", "tv_positionen_Flaeche",
                "tv_positionen_Einzelpreis"
            ]
        }

        # Beispiel: Definition der Beziehungen (Tab-übergreifend)
        # Diese Struktur beschreibt, wie Tabellen miteinander verbunden sind.
        self.relationships = {
            "tab_kunden": {
                "address": {
                    "table": "ADDRESSES",
                    "fields": self.tab_field_mapping["tab_kunden_address"],
                }
            },
            "tab_dienstleister": {
                "addresses": {
                    "table": "ADDRESSES",
                    "fields": self.tab_field_mapping["tab_dienstleister_address"],
                },
                "accounts": {
                    "table": "ACCOUNT",  # IBAN, Bankbeziehung
                    "fields": ["tv_dienstleister_IBAN", "tv_dienstleister_BIC", "tv_dienstleister_Kreditinstitut"],  # Passe die Feldnamen an deine GUI an!
                    # "iban_input" → IBAN, "bic_input" → BIC, "bankname_input" → Name der Bank
                }
            },
            "tab_rechnungen": {
                "customer": {
                    "table": "CUSTOMERS",
                    "fields": ["fk_custid"],  # z.B. als ComboBox oder LineEdit für Kundenauswahl
                },
                "service_provider": {
                    "table": "SERVICE_PROVIDER",
                    "fields": ["fk_ust_idnr"],  # z.B. als ComboBox oder LineEdit für Dienstleisterauswahl
                }
            },
            "tab_positionen": {
                "invoice": {
                    "table": "INVOICES",
                    "fields": ["fk_invoice_nr"],  # Rechnungsnummer als Fremdschlüssel
                }
            }
        }

        self.temp_positionen = []

        # Connect Signal for Tab Change
        self.tabWidget.currentChanged.connect(self.on_tab_changed)
        # set correct on start
        self.on_tab_changed(self.tabWidget.currentIndex())

        # Button-Einbindung für Speichern
        btn_speichern = self.findChild(QPushButton, "btn_eintrag_speichern")
        if btn_speichern:
            btn_speichern.clicked.connect(self.on_save_entry)

        self.init_tables()
        self.w_rechnung_hinzufuegen.setVisible(False)
        self.de_erstellungsdatum.setDate(date.today())
        self.showMaximized()
        btn_logo_upload = self.findChild(QPushButton, "btn_logo_upload")
        btn_logo_upload.clicked.connect(self.open_logo_picker)  

        # Variablen, um die ausgewählten IDs zu speichern
        self.selected_kunde_id = None
        self.selected_dienstleister_id = None
        self.init_tv_rechnungen_form_tabellen()

        btn_positionen_anlegen = self.findChild(QPushButton, "btn_positionen_anlegen")
        if btn_positionen_anlegen:
            btn_positionen_anlegen.clicked.connect(self.on_positionen_anlegen_clicked)

        btn_hinzufuegen = self.findChild(QPushButton, "btn_eintrag_hinzufuegen")
        if btn_hinzufuegen:
            btn_hinzufuegen.clicked.connect(self.clear_and_enable_form_fields)

        btn_felder_leeren = self.findChild(QPushButton, "btn_felder_leeren")
        if btn_felder_leeren:
            btn_felder_leeren.clicked.connect(self.clear_enabled_fields)

        self.findChild(QPushButton, "btn_eintrag_loeschen").clicked.connect(self.on_entry_delete)




    def open_logo_picker(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Logo auswählen", "", "Bilder (*.png *.jpg *.jpeg *.bmp *.svg);;Alle Dateien (*)")
        if file_path:
            print("Ausgewähltes Logo:", file_path)
            # Optional: Weiterverarbeitung, z. B. speichern oder anzeigen

    def init_tables(self):
        """
        Initializes all table views by loading data from corresponding database views.
        """
        for table_view_name, db_view_name in self.table_mapping.items():
            table_view = self.findChild(QTableView, table_view_name)
            if table_view:
                self.load_table(table_view, db_view_name)

    def load_table(self, table_view: QTableView, db_view: str):
        """
        Loads data into a QTableView from a database view.
        """
        try:
            data, columns = fetch_all(f"SELECT * FROM {db_view}")
        except Exception as e:
            error_message = f"Error while loading {db_view}: {format_exception(e)}"
            print(error_message)
            show_error(self, "Database Error", error_message)
            table_view.setModel(QStandardItemModel())
            return

        try:
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(columns)
            for row in data:
                items = [QStandardItem(str(cell)) for cell in row]
                for item in items:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                model.appendRow(items)

            table_view.setModel(model)
            table_view.resizeColumnsToContents()
            table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)

            header = table_view.horizontalHeader()
            for col in range(header.count()):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

            table_view.selectionModel().currentChanged.connect(
                lambda current, previous: self.on_row_selected(current, db_view, table_view)
            )
        except Exception as e:
            error_message = f"Error while populating table {db_view}: {format_exception(e)}"
            print(error_message)
            show_error(self, "Table Population Error", error_message)


    def clear_and_enable_form_fields(self):
        try:
            self.temp_positionen = []
            self.load_all_and_temp_positions_for_rechnungsformular()
            form_field_types = (QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit, QTextBrowser)
            for field in self.findChildren(form_field_types):
                if field.isVisible():
                    if isinstance(field, QLineEdit):
                        field.clear()
                    elif isinstance(field, QComboBox):
                        field.setCurrentIndex(-1)
                    elif isinstance(field, QDoubleSpinBox):
                        field.setValue(0.0)
                    elif isinstance(field, (QTextEdit, QPlainTextEdit, QTextBrowser)):
                        field.clear()
                    field.setEnabled(True)
            lbl_creation_date = self.findChild(QLabel, "lbl_eintrag_erstellt_datum")
            if lbl_creation_date:
                lbl_creation_date.setText("Erstellt am: N/A")

            # automatically set next free PK-Value
            current_tab = self.tabWidget.currentWidget().objectName()
            pk_conf = self.pk_field_config.get(current_tab)
            if pk_conf:
                pk_field_widget = self.findChild(QLineEdit, pk_conf["field"])
                if pk_field_widget:
                    next_pk = get_next_primary_key(self,
                        table_name=pk_conf["table"],
                        pk_column=pk_conf["pk_col"],
                        pk_type=pk_conf["type"]
                    )
                    pk_field_widget.setText(str(next_pk))

        except Exception as e:
            error_message = f"Error while clearing and enabling form fields: {format_exception(e)}"
            print(error_message)
            show_error(self, "Form Reset Error", error_message)

    def on_row_selected(self, current: QModelIndex, db_view: str, table_view: QTableView):
        """
        Handles the event when a row is selected in a table view.
        """
        if not current.isValid():
            return

        try:
            row_id = current.sibling(current.row(), 0).data()
            if table_view.objectName() in self.detail_mapping:
                if table_view.objectName() == "tv_rechnungen":
                    self.load_invoice_positions(row_id)
                elif table_view.objectName() == "tv_dienstleister":
                    self.load_service_provider_details(row_id)
            self.update_form_and_label(current, table_view)
        except Exception as e:
            error_message = f"Error handling row selection in {db_view}: {format_exception(e)}"
            print(error_message)
            show_error(self, "Row Selection Error", error_message)

    def update_form_and_label(self, current: QModelIndex, table_view: QTableView):
        """
        Updates the right-side form and lbl_eintrag_erstellt_datum with the selected row's data.
        """
        model = current.model()
        if not model:
            return

        try:
            for col in range(model.columnCount()):
                column_name = model.headerData(col, Qt.Orientation.Horizontal)
                value = current.sibling(current.row(), col).data()
                widget = self.findChild((QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit), f"{table_view.objectName()}_{column_name}")
                if isinstance(widget, QLineEdit):
                    widget.setText(str(value) if value is not None else "")
                    widget.setEnabled(False)
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(str(value) if value is not None else "0,00")
                    widget.setEnabled(False)
                elif isinstance(widget, QDoubleSpinBox):
                    try:
                        widget.setValue(float(value.replace(",", ".")) if value is not None else widget.setValue(0))
                    except (ValueError, TypeError):
                        widget.setValue(0)
                    widget.setEnabled(False)
                elif isinstance(widget, QTextEdit):
                    widget.setText(value if value is not None else "0,00")
                    widget.setEnabled(False)

            eintrag_datum = None
            for col in range(model.columnCount()):
                header = model.headerData(col, Qt.Orientation.Horizontal)
                if header == "Erstellungsdatum":
                    eintrag_datum = current.sibling(current.row(), col).data()
                    break

            lbl_creation_date = self.findChild(QLabel, "lbl_eintrag_erstellt_datum")
            if lbl_creation_date:
                lbl_creation_date.setText(f"Erstellt am: {eintrag_datum}" if eintrag_datum else "Erstellt am: N/A")
                if table_view.objectName() == "tv_dienstleister":
                    service_provider_id = current.sibling(current.row(), 0).data()
                    ceo_line_edit = self.findChild(QLineEdit, "tv_dienstleister_CEOS")
                    if ceo_line_edit:
                        ceo_names = get_ceos_for_service_provider_form(service_provider_id)
                        ceo_line_edit.setText(", ".join(ceo_names))
                        ceo_line_edit.setEnabled(False)
        except Exception as e:
            error_message = f"Error updating form and label: {format_exception(e)}"
            print(error_message)
            show_error(self, "Form Update Error", error_message)

    def load_service_provider_details(self, service_provider_id: str):
        """
        Loads CEO details for a selected service provider.
        """
        try:
            data = get_service_provider_ceos(service_provider_id)
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["ST_NR", "CEO Name"])
            for row in data:
                items = [QStandardItem(str(cell)) for cell in row]
                model.appendRow(items)
            self.tv_detail_dienstleister.setModel(model)
        except Exception as e:
            error_message = f"Error while loading CEO details: {format_exception(e)}"
            print(error_message)
            show_error(self, "Database Error", error_message)

    def load_invoice_positions(self, invoice_id: str):
        """
        Lädt alle Positionen zur gegebenen Rechnungsnummer über die m:n-Relation und zeigt sie im TableView an.
        """
        try:
            # Nur Positionen dieser Rechnung laden
            query = """
                SELECT
                    "Positions-ID",
                    Bezeichnung,
                    Beschreibung,
                    Einzelpreis,
                    Flaeche
                FROM view_positions_full
                WHERE Rechnungsnummer = ?
            """
            data, columns = fetch_all(query, (invoice_id,))
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(columns)
            for row in data:
                items = [QStandardItem(str(cell)) for cell in row]
                model.appendRow(items)
            self.tv_detail_rechnungen.setModel(model)
            self.tv_detail_rechnungen.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            self.tv_detail_rechnungen.setSelectionMode(QTableView.SelectionMode.SingleSelection)
            self.tv_detail_rechnungen.resizeColumnsToContents()
        except Exception as e:
            error_message = f"Error while loading invoice positions: {format_exception(e)}"
            print(error_message)
            show_error(self, "Database Error", error_message)

    def clear_enabled_fields(self):
        """
        Clears only the enabled fields of the current tab.
        """
        try:
            form_field_types = (QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit, QTextBrowser)
            for field in self.findChildren(form_field_types):
                if field.isVisible() and field.isEnabled():
                    if isinstance(field, QLineEdit):
                        field.clear()
                    elif isinstance(field, QComboBox):
                        field.setCurrentIndex(-1)
                    elif isinstance(field, QDoubleSpinBox):
                        field.setValue(0.0)
                    elif isinstance(field, (QTextEdit, QPlainTextEdit, QTextBrowser)):
                        field.clear()
        except Exception as e:
            error_message = f"Error while clearing enabled fields: {format_exception(e)}"
            print(error_message)
            show_error(self, "Field Clearing Error", error_message)

    def on_tab_changed(self, index):
        try:
            current_tab = self.tabWidget.widget(index)
            if current_tab is not None:
                tab_obj_name = current_tab.objectName()
                label_value = self.tab_search_label_text.get(tab_obj_name, "")
                lbl = self.findChild(QLabel, "lbl_search_for")
                if lbl:
                    lbl.setText(label_value)
        except Exception as e:
            print(f"Fehler beim Setzen des Suchlabels: {e}")

    def on_save_entry(self):
        current_tab = self.tabWidget.currentWidget().objectName()
        main_fields = self.tab_field_mapping.get(current_tab, [])
        rels = self.relationships.get(current_tab, {})

        # Hauptdaten validieren und sammeln
        valid, main_data, error = self.validate_and_collect_fields(main_fields)
        if not valid:
            show_error(self, "Validierungsfehler", error)
            return

        # Beziehungen mitsammeln (wenn weitere Relationen/Felder)
        rel_data = {}
        for rel, rel_info in rels.items():
            fields = rel_info["fields"]
            valid, sub_data, error = self.validate_and_collect_fields(fields)
            if not valid:
                show_error(self, "Validierungsfehler", error)
                return
            rel_data[rel] = sub_data

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()

                if current_tab == "tab_rechnungen":
                    # FKs holen wie gehabt
                    if "customer" in rel_data:
                        main_data["FK_CUSTID"] = rel_data["customer"].get("fk_custid",
                                                                          None) or self.get_selected_kunde_id()
                    else:
                        main_data["FK_CUSTID"] = self.get_selected_kunde_id()
                    if "service_provider" in rel_data:
                        main_data["FK_UST_IDNR"] = rel_data["service_provider"].get("fk_ust_idnr",
                                                                                    None) or self.get_selected_dienstleister_id()
                    else:
                        main_data["FK_UST_IDNR"] = self.get_selected_dienstleister_id()

                    # Rechnung speichern
                    cur.execute(
                        "INSERT INTO INVOICES (INVOICE_NR, CREATION_DATE, FK_CUSTID, FK_UST_IDNR, LABOR_COST, VAT_RATE_LABOR, VAT_RATE_POSITIONS) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            main_data["tb_rechnungsnummer"],
                            main_data["de_erstellungsdatum"],
                            main_data["FK_CUSTID"],
                            main_data["FK_UST_IDNR"],
                            main_data["dsb_lohnkosten"],
                            main_data["dsb_mwst_lohnkosten"],
                            main_data["dsb_mwst_positionen"]
                        )
                    )

                    # Positionen ANLEGEN und die Zuordnung in REF_INVOICES_POSITIONS herstellen!
                    for pos in self.temp_positionen:
                        cur.execute("SELECT COALESCE(MAX(POS_ID), 0) + 1 FROM POSITIONS")
                        next_pos_id = cur.fetchone()[0]
                        cur.execute(
                            "INSERT INTO POSITIONS (POS_ID, CREATION_DATE, DESCRIPTION, AREA, UNIT_PRICE, NAME) VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                next_pos_id,
                                main_data["de_erstellungsdatum"],
                                pos.get("DESCRIPTION", ""),
                                pos.get("AREA", 0),
                                pos.get("UNIT_PRICE", 0),
                                pos.get("NAME", ""),
                            )
                        )
                        # Die m:n-Zuordnung speichern:
                        cur.execute(
                            "INSERT INTO REF_INVOICES_POSITIONS (FK_POSITIONS_POS_ID, FK_INVOICES_INVOICE_NR) VALUES (?, ?)",
                            (next_pos_id, main_data["tb_rechnungsnummer"])
                        )

                        selected_indexes = self.tv_rechnungen_form_positionen.selectionModel().selectedRows()
                        for idx in selected_indexes:
                            pos_id = idx.sibling(idx.row(), 0).data()
                            if str(pos_id).startswith("NEU-"):
                                # Temporäre Position: erst speichern, dann verknüpfen
                                temp_index = int(str(pos_id).split("-")[1]) - 1
                                pos = self.temp_positionen[temp_index]
                                cur.execute(
                                    "INSERT INTO POSITIONS (CREATION_DATE, DESCRIPTION, AREA, UNIT_PRICE, NAME) VALUES (?, ?, ?, ?, ?)",
                                    (
                                        main_data["de_erstellungsdatum"],
                                        pos.get("DESCRIPTION", ""),
                                        pos.get("AREA", 0),
                                        pos.get("UNIT_PRICE", 0),
                                        pos.get("NAME", ""),
                                    )
                                )
                                new_pos_id = cur.lastrowid
                                cur.execute(
                                    "INSERT INTO REF_INVOICES_POSITIONS (FK_POSITIONS_POS_ID, FK_INVOICES_INVOICE_NR) VALUES (?, ?)",
                                    (new_pos_id, main_data["tb_rechnungsnummer"])
                                )
                            else:
                                # Bestehende Position: nur verknüpfen
                                cur.execute(
                                    "INSERT INTO REF_INVOICES_POSITIONS (FK_POSITIONS_POS_ID, FK_INVOICES_INVOICE_NR) VALUES (?, ?)",
                                    (int(pos_id), main_data["tb_rechnungsnummer"])
                                )

                elif current_tab == "tab_kunden":
                    # Adresse speichern und FK holen
                    address_id = None
                    if "address" in rel_data:
                        addr = rel_data["address"]
                        cur.execute(
                            "INSERT INTO ADDRESSES (STREET, NUMBER, CITY, ZIP, COUNTRY, CREATION_DATE) VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                addr.get("tv_kunden_Strasse", ""),
                                addr.get("tv_kunden_Hausnummer", ""),
                                addr.get("tv_kunden_Stadt", ""),
                                addr.get("tv_kunden_PLZ", ""),
                                addr.get("tv_kunden_Land", ""),
                                date.today().strftime("%d.%m.%Y")
                            )
                        )
                        address_id = cur.lastrowid

                    # Kunde speichern mit ADDRESS_ID als FK
                    cur.execute(
                        "INSERT INTO CUSTOMERS (CUSTID, FIRST_NAME, LAST_NAME, GENDER,CREATION_DATE, FK_ADDRESS_ID) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            main_data["tv_kunden_Kundennummer"],
                            main_data["tv_kunden_Vorname"],
                            main_data["tv_kunden_Nachname"],
                            main_data["tv_kunden_Geschlecht"],
                            date.today().strftime("%d.%m.%Y"),
                            address_id
                        )
                    )

                elif current_tab == "tab_dienstleister":
                    # 1. Adresse speichern
                    address_data = rel_data.get("addresses", {})
                    cur.execute(
                        "INSERT INTO ADDRESSES (STREET, NUMBER, CITY, ZIP, COUNTRY, CREATION_DATE) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            address_data.get("tv_dienstleister_Strasse", ""),
                            address_data.get("tv_dienstleister_Hausnummer", ""),
                            address_data.get("tv_dienstleister_Stadt", ""),
                            address_data.get("tv_dienstleister_PLZ", ""),
                            address_data.get("tv_dienstleister_Land", ""),
                            date.today().strftime("%d.%m.%Y")
                        )
                    )
                    address_id = cur.lastrowid

                    # 2. Logo speichern (optional, falls vorhanden)
                    logo_id = 1  # Setze ggf. richtige ID oder lass es bei Pflichtfeldern
                    # Beispiel: logo_id = deine_logo_speicherfunktion()

                    # 3. Dienstleister speichern
                    cur.execute(
                        "INSERT INTO SERVICE_PROVIDER (UST_IDNR, MOBILTELNR, PROVIDER_NAME, FAXNR, WEBSITE, EMAIL, TELNR, CREATION_DATE, FK_ADDRESS_ID, FK_LOGO_ID) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            main_data["tv_dienstleister_UStIdNr"],
                            main_data.get("tv_dienstleister_Mobiltelefonnummer", ""),
                            main_data["tv_dienstleister_Unternehmensname"],
                            main_data.get("tv_dienstleister_Faxnummer", ""),
                            main_data["tv_dienstleister_Webseite"],
                            main_data["tv_dienstleister_Email"],
                            main_data["tv_dienstleister_Telefonnummer"],
                            date.today().strftime("%d.%m.%Y"),
                            address_id,
                            logo_id
                        )
                    )

                    # 4. Bank prüfen und speichern
                    bank_data = rel_data.get("accounts", {})
                    bic = bank_data.get("tv_dienstleister_BIC", "")
                    bank_name = bank_data.get("tv_dienstleister_Kreditinstitut", "")
                    iban = bank_data.get("tv_dienstleister_IBAN", "")
                    if bic and bank_name:
                        cur.execute("SELECT COUNT(*) FROM BANK WHERE BIC=?", (bic,))
                        if cur.fetchone()[0] == 0:
                            cur.execute("INSERT INTO BANK (BIC, BANK_NAME) VALUES (?, ?)", (bic, bank_name))
                    # 5. Account speichern
                    if iban and bic:
                        cur.execute(
                            "INSERT INTO ACCOUNT (IBAN, FK_BANK_ID, FK_UST_IDNR) VALUES (?, ?, ?)",
                            (iban, bic, main_data["tv_dienstleister_UStIdNr"])
                        )

                    # 6. CEOs
                    ceo_names_text = main_data.get("tv_dienstleister_CEOS", "")
                    ceo_names = [n.strip() for n in ceo_names_text.split(",") if n.strip()]
                    if ceo_names:
                        # Steuernummern mit Dialog abfragen
                        ceo_dlg = CEOStNrDialog(ceo_names, self)
                        if ceo_dlg.exec() == QDialog.DialogCode.Accepted:
                            ceo_stnr_map = ceo_dlg.get_ceo_st_numbers()
                            for ceo_name, st_nr in ceo_stnr_map.items():
                                if ceo_name and st_nr:
                                    # CEO speichern, falls noch nicht vorhanden
                                    cur.execute("SELECT COUNT(*) FROM CEO WHERE ST_NR=?", (st_nr,))
                                    if cur.fetchone()[0] == 0:
                                        cur.execute("INSERT INTO CEO (ST_NR, CEO_NAME) VALUES (?, ?)", (st_nr, ceo_name))
                                    # REF_LABOR_COST speichern
                                    cur.execute(
                                        "INSERT INTO REF_LABOR_COST (FK_ST_NR, FK_UST_IDNR) VALUES (?, ?)",
                                        (st_nr, main_data["tv_dienstleister_UStIdNr"])
                                    )
                        else:
                            show_error(self, "Abbruch", "Speichern ohne Steuernummern nicht möglich.")
                            return
                elif current_tab == "tab_positionen":
                    # Position speichern
                    cur.execute(
                        "INSERT INTO POSITIONS (NAME, DESCRIPTION, AREA, UNIT_PRICE, CREATION_DATE) VALUES (?, ?, ?, ?, ?)",
                        (
                            main_data["tv_positionen_Bezeichnung"],
                            main_data["tv_positionen_Beschreibung"],
                            main_data["tv_positionen_Flaeche"],
                            main_data["tv_positionen_Einzelpreis"],
                            date.today().strftime("%d.%m.%Y")
                        )
                    )
                    pos_id = cur.lastrowid

                    # Optional: m:n-Zuordnung zu Rechnungen speichern, wenn im Formular möglich
                    if "invoice" in rel_data and rel_data["invoice"].get("fk_invoice_nr"):
                        invoice_nr = rel_data["invoice"]["fk_invoice_nr"]
                        cur.execute(
                            "INSERT INTO REF_INVOICES_POSITIONS (FK_POSITIONS_POS_ID, FK_INVOICES_INVOICE_NR) VALUES (?, ?)",
                            (pos_id, invoice_nr)
                        )

                conn.commit()
                self.refresh_tab_table_views()
                self.temp_positionen = []
                self.load_all_and_temp_positions_for_rechnungsformular()

            show_info(self, "Erfolg", "Eintrag erfolgreich gespeichert.")
            # Nach dem Speichern ggf. Felder leeren & Tabellen neu laden
            self.clear_and_enable_form_fields()
            self.init_tables()

        except Exception as e:
            show_error(self, "Speicherfehler", str(e))

    def validate_and_collect_fields(self, field_names):
        data_map = {}
        for field_name in field_names:
            widget = self.findChild(QWidget, field_name)
            if widget is None:
                continue
            value = None
            if isinstance(widget, QLineEdit):
                value = widget.text().strip()
            elif isinstance(widget, QComboBox):
                value = widget.currentText().strip()
            elif isinstance(widget, QDoubleSpinBox):
                value = widget.value()
            elif isinstance(widget, QTextEdit):
                value = widget.toPlainText()
            elif isinstance(widget, QDateEdit):
                value = widget.date().toString("dd.MM.yyyy")
            if value is None or (isinstance(value, str) and not value):
                label = self.findChild(QLabel,
                                       f"lbl_{field_name.replace('tv_', '').replace('tb_', '').replace('_input', '')}")
                field_label = label.text() if label else field_name
                return False, {}, f"Das Feld '{field_label}' darf nicht leer sein."
            data_map[field_name] = value
        return True, data_map, ""

    def init_tv_rechnungen_form_tabellen(self):
        # Kunden-Tabelle
        self.tv_rechnungen_form_kunde = self.findChild(QTableView, "tv_rechnungen_form_kunde")
        if self.tv_rechnungen_form_kunde:
            self.init_kunde_table()

        # Dienstleister-Tabelle
        self.tv_rechnungen_form_dienstleister = self.findChild(QTableView, "tv_rechnungen_form_dienstleister")
        if self.tv_rechnungen_form_dienstleister:
            self.init_dienstleister_table()

    def init_kunde_table(self):
        try:
            data, _ = fetch_all("SELECT CUSTID, FIRST_NAME || ' ' || LAST_NAME AS NAME FROM CUSTOMERS")
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["Kundennummer", "Name"])
            for row in data:
                items = [QStandardItem(str(cell)) for cell in row]
                for item in items:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                model.appendRow(items)
            self.tv_rechnungen_form_kunde.setModel(model)
            self.tv_rechnungen_form_kunde.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            self.tv_rechnungen_form_kunde.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.tv_rechnungen_form_kunde.selectionModel().selectionChanged.connect(self.on_kunde_selected)
            self.tv_rechnungen_form_kunde.resizeColumnsToContents()
        except Exception as e:
            show_error(self, "Fehler beim Laden der Kunden", str(e))

    def on_kunde_selected(self, selected, deselected):
        if not selected.indexes():
            self.selected_kunde_id = None
            return
        index = selected.indexes()[0]
        model = self.tv_rechnungen_form_kunde.model()
        if model:
            self.selected_kunde_id = model.item(index.row(), 0).text()

    def init_dienstleister_table(self):
        try:
            data, _ = fetch_all("SELECT UST_IDNR, PROVIDER_NAME FROM SERVICE_PROVIDER")
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["UStIdNr", "Unternehmensname"])
            for row in data:
                items = [QStandardItem(str(cell)) for cell in row]
                for item in items:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                model.appendRow(items)
            self.tv_rechnungen_form_dienstleister.setModel(model)
            self.tv_rechnungen_form_dienstleister.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            self.tv_rechnungen_form_dienstleister.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.tv_rechnungen_form_dienstleister.selectionModel().selectionChanged.connect(self.on_dienstleister_selected)
            self.tv_rechnungen_form_dienstleister.resizeColumnsToContents()
        except Exception as e:
            show_error(self, "Fehler beim Laden der Dienstleister", str(e))

    def on_dienstleister_selected(self, selected, deselected):
        if not selected.indexes():
            self.selected_dienstleister_id = None
            return
        index = selected.indexes()[0]
        model = self.tv_rechnungen_form_dienstleister.model()
        if model:
            self.selected_dienstleister_id = model.item(index.row(), 0).text()

    def update_positionen_tableview(self):
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["PositionsID", "Bezeichnung", "Beschreibung", "Einzelpreis", "Flaeche"])
        for pos in self.temp_positionen:
            items = [
                QStandardItem(str(pos.get("POS_ID", ""))),
                QStandardItem(str(pos.get("NAME", ""))),
                QStandardItem(str(pos.get("DESCRIPTION", ""))),
                QStandardItem(str(pos.get("UNIT_PRICE", ""))),
                QStandardItem(str(pos.get("AREA", ""))),
            ]
            for item in items:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            model.appendRow(items)
        self.tv_rechnungen_form_positionen.setModel(model)
        self.tv_rechnungen_form_positionen.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.tv_rechnungen_form_positionen.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.tv_rechnungen_form_positionen.resizeColumnsToContents()

    # Getter für die IDs bei Bedarf
    def get_selected_kunde_id(self):
        return self.selected_kunde_id

    def get_selected_dienstleister_id(self):
        return self.selected_dienstleister_id

    def on_positionen_anlegen_clicked(self):
        dlg = PositionDialog(self)
        if dlg.exec():
            pos_data = dlg.get_data()
            if not pos_data["NAME"]:
                show_error(self, "Fehler", "Bitte einen Namen angeben!")
                return
            # Rechnungsnummer für spätere Speicherung merken (optional für Validierung)
            rechnungsnummer_feld = self.findChild(QLineEdit, "tb_rechnungsnummer")
            rechnungsnummer = rechnungsnummer_feld.text() if rechnungsnummer_feld else ""
            if not rechnungsnummer:
                show_error(self, "Fehler", "Bitte zuerst eine Rechnungsnummer eintragen!")
                return
            # Noch keine POS_ID vergeben! Das macht später die DB.
            pos_data["FK_INVOICE_NR"] = rechnungsnummer
            self.temp_positionen.append(pos_data)
            self.load_all_and_temp_positions_for_rechnungsformular()

    def on_entry_delete(self):
        """
        Löscht je nach Tab Einträge und Beziehungen:
        - Rechnungen: Entfernt selektierte Positionen aus der m:n-Tabelle REF_INVOICES_POSITIONS. Ist keine Position mehr übrig und es ist nichts selektiert, wird die Rechnung gelöscht.
        - Aktualisiert immer die Detailansicht nach der Löschaktion.
        """
        current_tab = self.tabWidget.currentWidget().objectName()
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()

                if current_tab == "tab_rechnungen":
                    idx_rechnung = self.tv_rechnungen.currentIndex()
                    if not idx_rechnung.isValid():
                        show_error(self, "Nichts ausgewählt!", "Bitte wähle eine Rechnung aus!")
                        return
                    invoice_id = idx_rechnung.sibling(idx_rechnung.row(), 0).data()
                    pos_view = self.tv_detail_rechnungen
                    selected = pos_view.selectionModel().selectedRows() if pos_view.selectionModel() else []

                    if selected:
                        # Lösche die ausgewählten m:n Beziehungen (Positionen von Rechnung trennen)
                        for idx in selected:
                            pos_id = idx.sibling(idx.row(), 0).data()
                            cur.execute(
                                "DELETE FROM REF_INVOICES_POSITIONS WHERE FK_INVOICES_INVOICE_NR=? AND FK_POSITIONS_POS_ID=?",
                                (invoice_id, pos_id)
                            )
                        conn.commit()
                        show_info(self, "Erfolg", "Verknüpfung(en) erfolgreich gelöscht.")

                        # Detailansicht neu laden
                        self.refresh_tab_table_views() #Lade Form QTableViews neu

                        # Prüfen, ob noch Positionen übrig sind – falls nein, Detailansicht leeren
                        cur.execute("SELECT COUNT(*) FROM REF_INVOICES_POSITIONS WHERE FK_INVOICES_INVOICE_NR=?",
                                    (invoice_id,))
                        count = cur.fetchone()[0]
                        if count == 0:
                            self.tv_detail_rechnungen.setModel(QStandardItemModel())
                            show_info(self, "Hinweis",
                                      "Die Rechnung hat keine Positionen mehr. Sie kann jetzt gelöscht werden.")

                    else:
                        # Keine Position ausgewählt: Rechnung darf nur gelöscht werden, wenn keine Positionen mehr verknüpft sind
                        cur.execute("SELECT COUNT(*) FROM REF_INVOICES_POSITIONS WHERE FK_INVOICES_INVOICE_NR=?",
                                    (invoice_id,))
                        count = cur.fetchone()[0]
                        if count == 0:
                            cur.execute("DELETE FROM INVOICES WHERE INVOICE_NR=?", (invoice_id,))
                            conn.commit()
                            show_info(self, "Erfolg", "Rechnung gelöscht.")
                            # Gesamttabelle neu laden, Detailansicht leeren
                            self.refresh_tab_table_views() #Lade Form QTableViews neu
                        else:
                            show_error(self, "Nicht möglich", "Bitte zuerst alle Positionen entfernen!")

                elif current_tab == "tab_dienstleister":
                    idx = self.tv_dienstleister.currentIndex()
                    if not idx.isValid():
                        show_error(self, "Nichts ausgewählt!", "Bitte wähle einen Dienstleister aus!")
                        return
                    ust_idnr = idx.sibling(idx.row(), 0).data()
                    # Adresse-ID holen und löschen
                    cur.execute("SELECT FK_ADDRESS_ID FROM SERVICE_PROVIDER WHERE UST_IDNR=?", (ust_idnr,))
                    address_row = cur.fetchone()
                    if address_row:
                        address_id = address_row[0]
                        cur.execute("DELETE FROM ADDRESSES WHERE ID=?", (address_id,))
                    # IBAN/Account löschen (Bank bleibt!)
                    cur.execute("DELETE FROM ACCOUNT WHERE FK_UST_IDNR=?", (ust_idnr,))
                    # CEOs und RELATIONEN löschen
                    cur.execute("SELECT FK_ST_NR FROM REF_LABOR_COST WHERE FK_UST_IDNR=?", (ust_idnr,))
                    ceo_stnrs = [row[0] for row in cur.fetchall()]
                    for stnr in ceo_stnrs:
                        cur.execute("DELETE FROM CEO WHERE ST_NR=?", (stnr,))
                    cur.execute("DELETE FROM REF_LABOR_COST WHERE FK_UST_IDNR=?", (ust_idnr,))
                    # Dienstleister löschen
                    cur.execute("DELETE FROM SERVICE_PROVIDER WHERE UST_IDNR=?", (ust_idnr,))
                    conn.commit()
                    show_info(self, "Erfolg", "Dienstleister und zugehörige Daten gelöscht.")
                    self.refresh_tab_table_views() #Lade Form QTableViews neu

                elif current_tab == "tab_kunden":
                    idx = self.tv_kunden.currentIndex()
                    if not idx.isValid():
                        show_error(self, "Nichts ausgewählt!", "Bitte wähle einen Kunden aus!")
                        return
                    custid = idx.sibling(idx.row(), 0).data()
                    cur.execute("SELECT FK_ADDRESS_ID FROM CUSTOMERS WHERE CUSTID=?", (custid,))
                    address_row = cur.fetchone()
                    if address_row:
                        address_id = address_row[0]
                        cur.execute("DELETE FROM ADDRESSES WHERE ID=?", (address_id,))
                    cur.execute("DELETE FROM CUSTOMERS WHERE CUSTID=?", (custid,))
                    conn.commit()
                    show_info(self, "Erfolg", "Kunde und Adresse gelöscht.")
                    self.refresh_tab_table_views() #Lade Form QTableViews neu

                elif current_tab == "tab_positionen":
                    idx = self.tv_positionen.currentIndex()
                    if not idx.isValid():
                        show_error(self, "Nichts ausgewählt!", "Bitte wähle eine Position aus!")
                        return
                    pos_id = idx.sibling(idx.row(), 0).data()
                    cur.execute("DELETE FROM REF_INVOICES_POSITIONS WHERE FK_POSITIONS_POS_ID=?", (pos_id,))
                    cur.execute("DELETE FROM POSITIONS WHERE POS_ID=?", (pos_id,))
                    conn.commit()
                    show_info(self, "Erfolg", "Position und Verknüpfungen gelöscht.")
                    self.refresh_tab_table_views() #Lade Form QTableViews neu

        except Exception as e:
            show_error(self, "Löschfehler", str(e))

    def refresh_tab_table_views(self):
        """
        Aktualisiert alle QTableViews, die aktuell sichtbar sind –
        auch in verschachtelten Layouts und in Widgets wie w_rechnung_hinzufuegen.
        """

        # Hole das aktuelle Tab-Widget
        current_tab_widget = self.tabWidget.currentWidget()
        self.init_tv_rechnungen_form_tabellen()

        # Sammle alle QTableViews im Fenster
        all_table_views = self.findChildren(QTableView)
        for table_view in all_table_views:
            # Prüfe, ob TableView sichtbar ist (kaskadiert!):
            widget = table_view
            is_visible = widget.isVisible()
            # Prüfe, ob TableView Teil des aktuellen Tabs ODER eines dauerhaft sichtbaren Widgets (wie w_rechnung_hinzufuegen) ist
            # Wir gehen die Eltern-Kette hoch, bis wir beim Tab-Widget oder dem "Sonder-Widget" sind
            part_of_tab = False
            while widget is not None:
                if widget == current_tab_widget or widget.objectName() == "w_rechnung_hinzufuegen":
                    part_of_tab = True
                    break
                widget = widget.parent()
            if part_of_tab and is_visible:
                obj_name = table_view.objectName()
                db_view = self.table_mapping.get(obj_name)
                if db_view:
                    # Debug: print(f"Updating {obj_name} ({db_view})")
                    self.load_table(table_view, db_view)

    def load_all_and_temp_positions_for_rechnungsformular(self):
        """
        Lädt alle bestehenden Positionen aus der DB und fügt die noch nicht gespeicherten (temporären)
        Positionen aus self.temp_positionen hinzu. Zeigt alles im TableView 'tv_rechnungen_form_positionen' an.
        """
        try:
            # 1. Bestehende Positionen laden
            data, columns = fetch_all("SELECT POS_ID, NAME, DESCRIPTION, UNIT_PRICE, AREA FROM POSITIONS")

            # 2. Temporäre Positionen ergänzen (ohne POS_ID oder mit Platzhalter)
            temp_rows = []
            for idx, pos in enumerate(self.temp_positionen):
                temp_rows.append([
                    f"NEU-{idx + 1}",  # Platzhalter für neue POS_ID
                    pos.get("NAME", ""),
                    pos.get("DESCRIPTION", ""),
                    pos.get("UNIT_PRICE", ""),
                    pos.get("AREA", ""),
                ])

            # 3. Kombinieren
            all_rows = list(data) + temp_rows

            # 4. Anzeigen im Model
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["PositionsID", "Bezeichnung", "Beschreibung", "Einzelpreis", "Flaeche"])
            for row in all_rows:
                items = [QStandardItem(str(cell)) for cell in row]
                for item in items:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                model.appendRow(items)
            self.tv_rechnungen_form_positionen.setModel(model)
            self.tv_rechnungen_form_positionen.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            self.tv_rechnungen_form_positionen.setSelectionMode(QTableView.SelectionMode.MultiSelection)
            self.tv_rechnungen_form_positionen.resizeColumnsToContents()
        except Exception as e:
            show_error(self, "Fehler beim Laden der Positionen", str(e))