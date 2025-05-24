# IMPORT other Packages
import mimetypes
import os
import sqlite3
from datetime import date
import sys
# IMPORT PyQt6 Packages
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import QMainWindow, QTableView, QHeaderView, QLineEdit, QLabel, QComboBox, \
    QDoubleSpinBox, QPlainTextEdit, QTextBrowser, QTextEdit, QPushButton, QAbstractItemView, QWidget, QDateEdit, \
    QDialog, QFormLayout, QFileDialog
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QPixmap, QTextDocument
from PyQt6.QtCore import QModelIndex, Qt, QTimer
from PyQt6 import uic
# IMPORT Functions from local scripts
from database import get_next_primary_key, fetch_all
from config import UI_PATH, DB_PATH, POSITION_DIALOG_PATH, DEBOUNCE_TIME
from utils import show_error, format_exception, show_info
from logic import get_ceos_for_service_provider_form, get_service_provider_ceos

# Class :QDialog: for gathering StNr of CEOs
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

    # Function to get the data
    def get_ceo_st_numbers(self):
        return {ceo: field.text().strip() for ceo, field in self.ceo_fields.items()}

# Class :QDialog: for gathering data of new positions
class PositionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(POSITION_DIALOG_PATH, self)

    # Function to get the data
    def get_data(self):
        return {
            "NAME": self.le_name.text(),
            "DESCRIPTION": self.te_description.toPlainText(),
            "AREA": self.sb_area.value(),
            "UNIT_PRICE": self.sb_unit_price.value(),
        }

# Class :QMainWindow: for the whole UI functionality
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            # load UI file
            uic.loadUi(UI_PATH, self)
        except Exception as e:
            show_error(self, "UI Loading Error", f"Could not load UI file.\nError: {str(e)}")
            sys.exit(1)

        # Mapping: QTableViews to database views
        self.table_mapping = {
            "tv_rechnungen": "view_invoices_full",
            "tv_dienstleister": "view_service_provider_full",
            "tv_kunden": "view_customers_full",
            "tv_positionen": "view_positions_full",
        }

        # Mapping: QTableViews to detail QTableViews
        self.detail_mapping = {
            "tv_rechnungen": self.tv_detail_rechnungen,
            "tv_dienstleister": self.tv_detail_dienstleister,
        }

        # Mapping: QTableViews to PK column
        self.pk_field_config = {
            "tab_rechnungen": {"field": "tb_rechnungsnummer", "table": "INVOICES", "pk_col": "INVOICE_NR", "type": "invoice"},
            "tab_kunden": {"field": "tv_kunden_Kundennummer", "table": "CUSTOMERS", "pk_col": "CUSTID", "type": "customer"},
            "tab_dienstleister": {"field": "tv_dienstleister_UStIdNr", "table": "SERVICE_PROVIDER", "pk_col": "UST_IDNR", "type": "service_provider"},
            "tab_positionen": {"field": "tv_positionen_PositionsID", "table": "POSITIONS", "pk_col": "POS_ID", "type": "positions"}
        }

        # Mapping: Search label
        self.tab_search_label_text = {
            "tab_rechnungen": "Rechnungen durchsuchen",
            "tab_dienstleister": "Dienstleister durchsuchen",
            "tab_kunden": "Kunden durchsuchen",
            "tab_positionen": "Positionen durchsuchen"
        }

        # Mapping: Form fields to QTabs
        self.tab_field_mapping = {
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
            "tab_rechnungen": [
                "tb_rechnungsnummer", "de_erstellungsdatum", "dsb_lohnkosten", "dsb_mwst_lohnkosten", "dsb_mwst_positionen"
            ],
            "tab_rechnungen_fk": [
                "fk_custid", "fk_ust_idnr"
            ],
            "tab_positionen": [
                "tv_positionen_PositionsID", "tv_positionen_Bezeichnung", "tv_positionen_Beschreibung", "tv_positionen_Flaeche",
                "tv_positionen_Einzelpreis"
            ]
        }

        # Mapping: Relationships between the Tables/QTableViews/QTabs
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
                    "table": "ACCOUNT",
                    "fields": ["tv_dienstleister_IBAN", "tv_dienstleister_BIC", "tv_dienstleister_Kreditinstitut"],
                }
            },
            "tab_rechnungen": {
                "customer": {
                    "table": "CUSTOMERS",
                    "fields": ["fk_custid"],
                },
                "service_provider": {
                    "table": "SERVICE_PROVIDER",
                    "fields": ["fk_ust_idnr"],
                }
            },
            "tab_positionen": {
                "invoice": {
                    "table": "INVOICES",
                    "fields": ["fk_invoice_nr"],
                }
            }
        }

        # Initiation of UI and program itself
        self.temp_positionen = []
        self.init_tables()
        self.w_rechnung_hinzufuegen.setVisible(False)
        self.de_erstellungsdatum.setDate(date.today())
        self.showMaximized()
        self.selected_kunde_id = None
        self.selected_dienstleister_id = None
        self.init_tv_rechnungen_form_tabellen()

        # Connect Signal for Tab Change
        self.tabWidget.currentChanged.connect(self.on_tab_changed)
        # set correct on start
        self.on_tab_changed(self.tabWidget.currentIndex())
        self.update_export_button_state(self.tabWidget.currentIndex())

        # Connect Signal for Click on 'btn_eintrag_speichern'
        btn_speichern = self.findChild(QPushButton, "btn_eintrag_speichern")
        if btn_speichern:
            btn_speichern.clicked.connect(self.on_save_entry)

        # Connect Signal for Click on 'btn_logo_upload'
        btn_logo_upload = self.findChild(QPushButton, "btn_logo_upload")
        if btn_logo_upload:
            btn_logo_upload.clicked.connect(self.open_logo_picker)

        # Connect Signal for Click on 'btn_positionen_anlegen'
        btn_positionen_anlegen = self.findChild(QPushButton, "btn_positionen_anlegen")
        if btn_positionen_anlegen:
            btn_positionen_anlegen.clicked.connect(self.on_positionen_anlegen_clicked)

        # Connect Signal for Click on 'btn_eintrag_hinzufuegen'
        btn_hinzufuegen = self.findChild(QPushButton, "btn_eintrag_hinzufuegen")
        if btn_hinzufuegen:
            btn_hinzufuegen.clicked.connect(self.clear_and_enable_form_fields)

        # Connect Signal for Click on 'btn_felder_leeren'
        btn_felder_leeren = self.findChild(QPushButton, "btn_felder_leeren")
        if btn_felder_leeren:
            btn_felder_leeren.clicked.connect(self.clear_and_enable_form_fields)

        # Connect Signal for Click on 'btn_eintrag_loeschen'
        btn_eintrag_loeschen = self.findChild(QPushButton, "btn_eintrag_loeschen")
        if btn_eintrag_loeschen:
            btn_eintrag_loeschen.clicked.connect(self.on_entry_delete)

        # Connect Signal for Click on 'btn_rechnung_exportieren'
        self.btn_rechnung_exportieren = self.findChild(QPushButton, "btn_rechnung_exportieren")
        if self.btn_rechnung_exportieren:
            self.btn_rechnung_exportieren.clicked.connect(self.on_rechnung_exportieren_clicked)

        # Set DEBOUNCE Timer for every search field
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.tb_search_entries.textChanged.connect(self.on_search_text_changed)

        self.search_timer_kunden = QTimer(self)
        self.search_timer_kunden.setSingleShot(True)
        self.search_timer_kunden.timeout.connect(self.search_kunden)

        self.search_timer_dienstleister = QTimer(self)
        self.search_timer_dienstleister.setSingleShot(True)
        self.search_timer_dienstleister.timeout.connect(self.search_dienstleister)

        self.search_timer_positionen = QTimer(self)
        self.search_timer_positionen.setSingleShot(True)
        self.search_timer_positionen.timeout.connect(self.search_positionen)

        # get QLineEdit search fields in Rechnungen Form
        self.le_search_kunden = self.findChild(QLineEdit, "tb_search_kunden")
        self.le_search_dienstleister = self.findChild(QLineEdit, "tb_search_dienstleister")
        self.le_search_positionen = self.findChild(QLineEdit, "tb_search_positionen")

        # Connect Signal for Text Changed on QLineEdit search fields in Rechnungen Form
        if self.le_search_kunden:
            self.le_search_kunden.textChanged.connect(self.on_search_kunden_text_changed)
        if self.le_search_dienstleister:
            self.le_search_dienstleister.textChanged.connect(self.on_search_dienstleister_text_changed)
        if self.le_search_positionen:
            self.le_search_positionen.textChanged.connect(self.on_search_positionen_text_changed)


    # Initializes all table views by loading data from corresponding database views
    def init_tables(self):
        for table_view_name, db_view_name in self.table_mapping.items():
            table_view = self.findChild(QTableView, table_view_name)
            if table_view:
                self.load_table(table_view, db_view_name)

    # Loads data into a QTableView from a database view.
    def load_table(self, table_view: QTableView, db_view: str):
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

    # Clears and enables all form fields
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

    # Handles the event when a row is selected in a table view
    def on_row_selected(self, current: QModelIndex, db_view: str, table_view: QTableView):
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

    # Updates the current form and lbl_eintrag_erstellt_datum with the selected row's data
    def update_form_and_label(self, current: QModelIndex, table_view: QTableView):
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

    # Loads CEO details for a selected service provider
    def load_service_provider_details(self, service_provider_id: str):
        try:
            data = get_service_provider_ceos(service_provider_id)
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["ST_NR", "CEO Name"])
            for row in data:
                items = [QStandardItem(str(cell)) for cell in row]
                model.appendRow(items)
            self.tv_detail_dienstleister.setModel(model)
            self.show_service_provider_logo(service_provider_id)
        except Exception as e:
            error_message = f"Error while loading CEO details: {format_exception(e)}"
            print(error_message)
            show_error(self, "Database Error", error_message)

    # Loads all positions for selected row from INVOICE_ID
    def load_invoice_positions(self, invoice_id: str):
        try:
            # Nur Positionen dieser Rechnung laden
            query = """
                SELECT
                    PositionsID,
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

    # Updates 'lbl_search_for' with corresponding tab name
    def on_tab_changed(self, index):
        try:
            self.update_export_button_state
            current_tab = self.tabWidget.widget(index)
            if current_tab is not None:
                tab_obj_name = current_tab.objectName()
                label_value = self.tab_search_label_text.get(tab_obj_name, "")
                lbl = self.findChild(QLabel, "lbl_search_for")
                if lbl:
                    lbl.setText(label_value)
        except Exception as e:
            print(f"Fehler beim Setzen des Suchlabels: {e}")

    # Saves and commits the data from form current form into DB
    def on_save_entry(self):
        current_tab = self.tabWidget.currentWidget().objectName()
        main_fields = self.tab_field_mapping.get(current_tab, [])
        rels = self.relationships.get(current_tab, {})

        # check validation of entered data
        valid, main_data, error = self.validate_and_collect_fields(main_fields)
        if not valid:
            show_error(self, "Validierungsfehler", error)
            return

        # Collects realtion data for corresponding case
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

                # --------------RECHNUNGEN-------------------
                if current_tab == "tab_rechnungen":
                    # Creates data array for Tab Rechnungen
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

                    # INSERT collected data into INVOICES
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

                    # Collect only selected positions
                    selected_indexes = self.tv_rechnungen_form_positionen.selectionModel().selectedRows()
                    for idx in selected_indexes:
                        pos_id = idx.sibling(idx.row(), 0).data()
                        if str(pos_id).startswith("NEU-"):
                            # Collect and connect temporary positions (when created via the + button)
                            temp_index = int(str(pos_id).split("-")[1]) - 1
                            pos = self.temp_positionen[temp_index]
                            # INSERT collected data into POSITIONS
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
                            # INSERT collected data into REF_INVOICES_POSITIONS (for temporary positions)
                            cur.execute(
                                "INSERT INTO REF_INVOICES_POSITIONS (FK_POSITIONS_POS_ID, FK_INVOICES_INVOICE_NR) VALUES (?, ?)",
                                (new_pos_id, main_data["tb_rechnungsnummer"])
                            )
                        else:
                            # INSERT collected data into REF_INVOICES_POSITIONS (for existing positions)
                            cur.execute(
                                "INSERT INTO REF_INVOICES_POSITIONS (FK_POSITIONS_POS_ID, FK_INVOICES_INVOICE_NR) VALUES (?, ?)",
                                (int(pos_id), main_data["tb_rechnungsnummer"])
                            )

                    # Clear temporary positions after Saving
                    self.temp_positionen = []
                    # Reload all QTableViews
                    self.load_all_and_temp_positions_for_rechnungsformular()


                #--------------KUNDEN-------------------
                elif current_tab == "tab_kunden":
                    # INSERT collected data into ADDRESSES
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

                    # INSERT collected data into CUSTOMERS
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


                # --------------DIENSTLEISTER-------------------
                elif current_tab == "tab_dienstleister":
                    address_data = rel_data.get("addresses", {})

                    # INSERT collected data into ADDRESSES
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
                    logo_id = None
                    # Checks if user selected a valid file
                    if (self.file_name
                            and self.logo_data
                            and len(self.logo_data) > 0):
                        logo_file_name = self.file_name
                        logo_data = self.logo_data
                        file_type = self.mime_type or ""
                        # INSERT collected data into LOGOS
                        cur.execute(
                            "INSERT INTO LOGOS (FILE_NAME, LOGO_BINARY, MIME_TYPE, CREATION_DATE) VALUES (?, ?, ?, ?)",
                            (
                                logo_file_name,
                                logo_data,
                                file_type,
                                date.today().strftime("%d.%m.%Y"),
                            )
                        )
                        logo_id = cur.lastrowid

                    else:
                        show_error(self, "Fehler", "Fehler beim Speichern des Logos")

                    # INSERT collected data into SERVICE_PROVIDER
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

                    # Checks if Bank exists and INSERT collected data into ACCOUNT NAD BANK
                    bank_data = rel_data.get("accounts", {})
                    bic = bank_data.get("tv_dienstleister_BIC", "")
                    bank_name = bank_data.get("tv_dienstleister_Kreditinstitut", "")
                    iban = bank_data.get("tv_dienstleister_IBAN", "")
                    if bic and bank_name:
                        cur.execute("SELECT COUNT(*) FROM BANK WHERE BIC=?", (bic,))
                        if cur.fetchone()[0] == 0:
                            cur.execute("INSERT INTO BANK (BIC, BANK_NAME) VALUES (?, ?)", (bic, bank_name))
                    if iban and bic:
                        cur.execute(
                            "INSERT INTO ACCOUNT (IBAN, FK_BANK_ID, FK_UST_IDNR) VALUES (?, ?, ?)",
                            (iban, bic, main_data["tv_dienstleister_UStIdNr"])
                        )

                    # Strips the collected CEOs list
                    ceo_names_text = main_data.get("tv_dienstleister_CEOS", "")
                    ceo_names = [n.strip() for n in ceo_names_text.split(",") if n.strip()]

                    # Opens the :QDialog: CEOStNrDialog and gathers StNr for every CEO
                    if ceo_names:
                        ceo_dlg = CEOStNrDialog(ceo_names, self)
                        if ceo_dlg.exec() == QDialog.DialogCode.Accepted:
                            ceo_stnr_map = ceo_dlg.get_ceo_st_numbers()
                            for ceo_name, st_nr in ceo_stnr_map.items():
                                if ceo_name and st_nr:
                                    # INSERT collected data into CEO
                                    cur.execute("SELECT COUNT(*) FROM CEO WHERE ST_NR=?", (st_nr,))
                                    if cur.fetchone()[0] == 0:
                                        cur.execute("INSERT INTO CEO (ST_NR, CEO_NAME) VALUES (?, ?)",
                                                    (st_nr, ceo_name))
                                    # INSERT collected data into REF_LABOR_COST
                                    cur.execute(
                                        "INSERT INTO REF_LABOR_COST (FK_ST_NR, FK_UST_IDNR) VALUES (?, ?)",
                                        (st_nr, main_data["tv_dienstleister_UStIdNr"])
                                    )
                        else:
                            show_error(self, "Abbruch", "Speichern ohne Steuernummern nicht möglich.")
                            return


                # --------------POSITIONEN-------------------
                elif current_tab == "tab_positionen":
                    # INSERT collected data into POSITIONS
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

                # Commits current Session into DB
                conn.commit()
                # Reloads all QTableViews
                self.refresh_tab_table_views()
                # Clear QTableViews in
                self.load_all_and_temp_positions_for_rechnungsformular()

            show_info(self, "Erfolg", "Eintrag erfolgreich gespeichert.")
            # Nach dem Speichern ggf. Felder leeren & Tabellen neu laden
            self.clear_and_enable_form_fields()
            self.init_tables()

        except Exception as e:
            show_error(self, "Speicherfehler", str(e))

    # Validates collected data before commiting into DB
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

    # Initializes QTableViews in Rechnungen Form
    def init_tv_rechnungen_form_tabellen(self):
        # Kunden QTableView
        self.tv_rechnungen_form_kunde = self.findChild(QTableView, "tv_rechnungen_form_kunde")
        if self.tv_rechnungen_form_kunde:
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

        # Dienstleister QTableView
        self.tv_rechnungen_form_dienstleister = self.findChild(QTableView, "tv_rechnungen_form_dienstleister")
        if self.tv_rechnungen_form_dienstleister:
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
                self.tv_rechnungen_form_dienstleister.selectionModel().selectionChanged.connect(
                    self.on_dienstleister_selected)
                self.tv_rechnungen_form_dienstleister.resizeColumnsToContents()
            except Exception as e:
                show_error(self, "Fehler beim Laden der Dienstleister", str(e))

#********************************************************************************************
#
#               Hier weitermachen mit Code kommentieren und aufhübschen
#
#********************************************************************************************

    def on_kunde_selected(self, selected, deselected):
        if not selected.indexes():
            self.selected_kunde_id = None
            return
        index = selected.indexes()[0]
        model = self.tv_rechnungen_form_kunde.model()
        if model:
            self.selected_kunde_id = model.item(index.row(), 0).text()

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
        Zeigt im TableView 'tv_rechnungen_form_positionen':
        - Wenn Suchfeld leer: temp-array oben, dann alle DB-Positionen
        - Wenn Suchfeld nicht leer: nur gefilterte DB-Positionen (temp-array ignorieren)
        """
        try:
            le_search_positionen = self.findChild(QLineEdit, "tb_search_positionen")
            search_text = le_search_positionen.text().strip() if le_search_positionen else ""

            if search_text:
                # Nur DB durchsuchen, temp-array ignorieren
                _, columns = fetch_all(f"SELECT * FROM view_positions_full LIMIT 1")
                like_clauses = [f'"{col}" LIKE ?' for col in columns]
                sql = f'SELECT * FROM view_positions_full WHERE ' + " OR ".join(like_clauses)
                params = [f'%{search_text}%'] * len(columns)
                data, _ = fetch_all(sql, tuple(params))
                all_rows = list(data)
            else:
                # temp-array oben, dann alle DB-Positionen
                data, columns = fetch_all("SELECT POS_ID, NAME, DESCRIPTION, UNIT_PRICE, AREA FROM POSITIONS")
                temp_rows = []
                for idx, pos in enumerate(self.temp_positionen):
                    temp_rows.append([
                        f"NEU-{idx + 1}",
                        pos.get("NAME", ""),
                        pos.get("DESCRIPTION", ""),
                        pos.get("UNIT_PRICE", ""),
                        pos.get("AREA", ""),
                    ])
                all_rows = temp_rows + list(data)

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

    def search_entries(self):
        search_text_widget = self.findChild(QLineEdit, "tb_search_entries")
        if not search_text_widget:
            return
        search_text = search_text_widget.text().strip()
        if not search_text:
            # Wenn kein Suchtext, Tabelle normal laden
            current_tab = self.tabWidget.currentWidget().objectName()
            table_view_name = None
            db_view_name = None
            for k, v in self.table_mapping.items():
                if k.replace("tv_", "tab_") == current_tab or k == f"tv_{current_tab.replace('tab_', '')}":
                    table_view_name = k
                    db_view_name = v
            if table_view_name and db_view_name:
                table_view = self.findChild(QTableView, table_view_name)
                if table_view:
                    self.load_table(table_view, db_view_name)
            return

        # --- Erweiterte Suche mit mehreren Begriffen ---
        # Split nach Leerzeichen, entferne leere Strings
        search_terms = [term.strip() for term in search_text.split() if term.strip()]
        if not search_terms:
            return

        current_tab = self.tabWidget.currentWidget().objectName()
        table_view_name = None
        db_view_name = None
        for k, v in self.table_mapping.items():
            if k.replace("tv_", "tab_") == current_tab or k == f"tv_{current_tab.replace('tab_', '')}":
                table_view_name = k
                db_view_name = v
        if not db_view_name:
            return

        try:
            # Spaltennamen holen
            _, columns = fetch_all(f"SELECT * FROM {db_view_name} LIMIT 1")
            # Baue WHERE: für jedes Suchwort muss es in mindestens einer Spalte vorkommen
            like_clauses = []
            params = []
            for term in search_terms:
                or_parts = [f'"{col}" LIKE ?' for col in columns]
                like_clauses.append('(' + ' OR '.join(or_parts) + ')')
                params.extend([f'%{term}%'] * len(columns))
            # Alle Begriffe müssen irgendwo passen: UND-Verknüpfung
            where_clause = ' AND '.join(like_clauses)
            sql = f'SELECT * FROM {db_view_name} WHERE {where_clause}'
            data, _ = fetch_all(sql, tuple(params))

            # Anzeige aktualisieren
            table_view = self.findChild(QTableView, table_view_name)
            if table_view:
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
        except Exception as e:
            show_error(self, "Suchfehler", str(e))

    # debouncing funktion verhindert performance crashes/probleme
    def on_search_text_changed(self, text):
        self.search_timer.stop()
        self.search_timer.timeout.connect(self.search_entries)
        self.search_timer.start(DEBOUNCE_TIME)  # DEBOUNCE_TIME warten

    def update_export_button_state(self, index):
        current_tab = self.tabWidget.widget(index)
        if not self.btn_rechnung_exportieren:
            return
        if current_tab and current_tab.objectName() == "tab_rechnungen":
            self.btn_rechnung_exportieren.setEnabled(True)
        else:
            self.btn_rechnung_exportieren.setEnabled(False)

    def on_rechnung_exportieren_clicked(self):
        idx = self.tv_rechnungen.currentIndex()
        if not idx.isValid():
            show_error(self, "Keine Auswahl", "Bitte zuerst eine Rechnung auswählen!")
            return
        invoice_nr = idx.sibling(idx.row(), 0).data()

        try:
            # === Datenbankabfrage wie bisher ===
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()

                # Rechnungsdaten
                cur.execute("SELECT * FROM INVOICES WHERE INVOICE_NR = ?", (invoice_nr,))
                invoice_row = cur.fetchone()
                invoice_columns = [desc[0] for desc in cur.description]

                # Kunde
                cur.execute("""
                    SELECT c.*, a.*
                    FROM CUSTOMERS c
                    LEFT JOIN ADDRESSES a ON c.FK_ADDRESS_ID = a.ID
                    WHERE c.CUSTID = (SELECT FK_CUSTID FROM INVOICES WHERE INVOICE_NR = ?)
                """, (invoice_nr,))
                customer_row = cur.fetchone()
                customer_columns = [desc[0] for desc in cur.description]

                # Dienstleister
                cur.execute("""
                    SELECT s.*, a.*
                    FROM SERVICE_PROVIDER s
                    LEFT JOIN ADDRESSES a ON s.FK_ADDRESS_ID = a.ID
                    WHERE s.UST_IDNR = (SELECT FK_UST_IDNR FROM INVOICES WHERE INVOICE_NR = ?)
                """, (invoice_nr,))
                provider_row = cur.fetchone()
                provider_columns = [desc[0] for desc in cur.description]

                # CEOs zum Dienstleister
                cur.execute("""
                    SELECT ceo.ST_NR, ceo.CEO_NAME
                    FROM SERVICE_PROVIDER sp
                    JOIN REF_LABOR_COST rel ON rel.FK_UST_IDNR = sp.UST_IDNR
                    JOIN CEO ceo ON rel.FK_ST_NR = ceo.ST_NR
                    WHERE sp.UST_IDNR = (SELECT FK_UST_IDNR FROM INVOICES WHERE INVOICE_NR = ?)
                """, (invoice_nr,))
                ceos_rows = cur.fetchall()
                ceos_columns = [desc[0] for desc in cur.description]

                # Positionen
                cur.execute("""
                    SELECT p.*
                    FROM REF_INVOICES_POSITIONS ref
                    JOIN POSITIONS p ON ref.FK_POSITIONS_POS_ID = p.POS_ID
                    WHERE ref.FK_INVOICES_INVOICE_NR = ?
                """, (invoice_nr,))
                positions_rows = cur.fetchall()
                positions_columns = [desc[0] for desc in cur.description]

            export_data = [
                {"invoice": dict(zip(invoice_columns, invoice_row)) if invoice_row else {}},
                {"customer": dict(zip(customer_columns, customer_row)) if customer_row else {}},
                {"service_provider": dict(zip(provider_columns, provider_row)) if provider_row else {}},
                {"ceos": [dict(zip(ceos_columns, row)) for row in ceos_rows]},
                {"positions": [dict(zip(positions_columns, row)) for row in positions_rows]}
            ]

            # === PDF-Export Teil ===
            save_path, _ = QFileDialog.getSaveFileName(self, "Rechnung als PDF speichern", "", "PDF-Dateien (*.pdf)")
            if not save_path:
                return

            html = self.build_invoice_html(export_data)
            doc = QTextDocument()
            doc.setHtml(html)
            printer = QPrinter()
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(save_path)
            doc.print(printer)
            show_info(self, "Export", f"Rechnung erfolgreich als PDF exportiert: {save_path}")

        except Exception as e:
            show_error(self, "Export-Fehler", str(e))

    def on_search_kunden_text_changed(self, text):
        self.search_timer_kunden.stop()
        self.search_timer_kunden.start(DEBOUNCE_TIME)

    def search_kunden(self):
        self._search_in_table(
            search_lineedit_name="tb_search_kunden",
            table_view_name="tv_rechnungen_form_kunde",
            db_view_name="view_customers_full"
        )

    def on_search_dienstleister_text_changed(self, text):
        self.search_timer_dienstleister.stop()
        self.search_timer_dienstleister.start(DEBOUNCE_TIME)

    def search_dienstleister(self):
        self._search_in_table(
            search_lineedit_name="tb_search_dienstleister",
            table_view_name="tv_rechnungen_form_dienstleister",
            db_view_name="view_service_provider_full"
        )

    def on_search_positionen_text_changed(self, text):
        self.search_timer_positionen.stop()
        self.search_timer_positionen.start(DEBOUNCE_TIME)

    def search_positionen(self):
        """
        Sucht in Haupt-Tabelle (tv_positionen) und aktualisiert auch das Rechnungsformular-TableView.
        """
        # Haupt-TableView (tv_positionen): nur DB, wie gehabt
        self._search_in_table(
            search_lineedit_name="tb_search_positionen",
            table_view_name="tv_positionen",
            db_view_name="view_positions_full"
        )
        # Rechnungsformular-TableView (tv_rechnungen_form_positionen): immer auch aktualisieren!
        self.load_all_and_temp_positions_for_rechnungsformular()

    def _search_in_table(self, search_lineedit_name, table_view_name, db_view_name):
        search_box = self.findChild(QLineEdit, search_lineedit_name)
        if not search_box:
            return
        search_text = search_box.text().strip()
        table_view = self.findChild(QTableView, table_view_name)
        if not table_view:
            return

        if not search_text:
            self.load_table(table_view, db_view_name)
            return

        try:
            _, columns = fetch_all(f"SELECT * FROM {db_view_name} LIMIT 1")
            like_clauses = [f'"{col}" LIKE ?' for col in columns]
            sql = f'SELECT * FROM {db_view_name} WHERE ' + " OR ".join(like_clauses)
            params = [f'%{search_text}%'] * len(columns)
            data, _ = fetch_all(sql, tuple(params))

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
        except Exception as e:
            show_error(self, "Suchfehler", str(e))

    def open_logo_picker(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Logo auswählen",
            "",
            "Bilder (*.png *.jpg *.jpeg *.bmp *.svg);;Alle Dateien (*)"
        )
        if file_path:
            self.selected_files = [file_path]
            if hasattr(self, "fileListWidget"):
                self.fileListWidget.clear()
                self.fileListWidget.addItem(file_path)
            self.file_path = file_path
            self.file_name = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                self.logo_data = f.read()
            mime_type, _ = mimetypes.guess_type(file_path)
            self.mime_type = mime_type
            print("Bild gewählt:", self.file_name)
            print("MIME-Type:", self.mime_type)
        else:
            self.selected_files = []
            self.file_path = None
            self.file_name = None
            self.logo_data = None
            self.mime_type = None
            if hasattr(self, "fileListWidget"):
                self.fileListWidget.clear()

    def show_service_provider_logo(self, ust_idnr):
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT l.LOGO_BINARY
                FROM SERVICE_PROVIDER s
                JOIN LOGOS l ON s.FK_LOGO_ID = l.ID
                WHERE s.UST_IDNR = ?
            """, (ust_idnr,))
            row = cur.fetchone()
            label = self.findChild(QLabel, "lbl_dienstleister_logo")
            if label:
                if row and row[0]:
                    pixmap = QPixmap()
                    pixmap.loadFromData(row[0])
                    # Skaliere das Bild so, dass das Seitenverhältnis erhalten bleibt:
                    scaled_pixmap = pixmap.scaled(
                        label.width(),
                        label.height(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    label.setPixmap(scaled_pixmap)
                    label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    label.setScaledContents(False)
                else:
                    label.clear()

    def build_invoice_html(self, export_data):
        invoice = export_data[0]['invoice']
        customer = export_data[1]['customer']
        service_provider = export_data[2]['service_provider']
        ceos = export_data[3]['ceos']
        positions = export_data[4]['positions']

        # Summen berechnen (anpassen je nach Feldern in deiner Datenbank)
        total_net = sum(float(pos.get("UNIT_PRICE", 0)) * float(pos.get("AREA", 0)) for pos in positions)
        vat = float(invoice.get('VAT_RATE_LABOR', 19))
        total_vat = total_net * vat / 100
        total_gross = total_net + total_vat

        # Positionen als HTML-Tabelle
        pos_rows = ""
        for idx, pos in enumerate(positions, 1):
            pos_rows += f"""
            <tr>
                <td style="padding:4px;">{idx}</td>
                <td style="padding:4px;">
                    <b>{pos.get("NAME", "")}</b><br>
                    <span style="font-size:10pt;">{pos.get("DESCRIPTION", "")}</span>
                </td>
                <td style="padding:4px;text-align:right;">{pos.get("AREA", "")} m&sup2;</td>
                <td style="padding:4px;text-align:right;">{float(pos.get("UNIT_PRICE", 0)):.2f} &euro;</td>
                <td style="padding:4px;text-align:right;">{float(pos.get("AREA", 0)) * float(pos.get("UNIT_PRICE", 0)):.2f} &euro;</td>
            </tr>
            """

        # CEOs als Aufzählung, falls gewünscht
        ceo_rows = "<br>".join(f"{ceo['CEO_NAME']} (St.-Nr.: {ceo['ST_NR']})" for ceo in ceos) if ceos else ""

        html = f"""
        <html>
        <head>
        <style>
        body {{ font-family: Arial, sans-serif; font-size: 11pt; }}
        .header-table td {{ vertical-align:top; }}
        .summary-table td {{ padding:3px 10px; }}
        </style>
        </head>
        <body>
        <table width="100%" class="header-table">
            <tr>
                <td>
                    <h2 style="margin-bottom:0;">{service_provider.get('PROVIDER_NAME', '')}</h2>
                    {service_provider.get('STREET', '')} {service_provider.get('NUMBER', '')}<br>
                    {service_provider.get('ZIP', '')} {service_provider.get('CITY', '')}
                </td>
                <td align="right">
                    <!-- Firmenlogo kann per <img> eingebunden werden -->
                </td>
            </tr>
        </table>
        <hr>
        <table width="100%">
            <tr>
                <td>
                    <b>Rechnung an:</b><br>
                    {customer.get('FIRST_NAME', '')} {customer.get('LAST_NAME', '')}<br>
                    {customer.get('STREET', '')} {customer.get('NUMBER', '')}<br>
                    {customer.get('ZIP', '')} {customer.get('CITY', '')}
                </td>
                <td align="right">
                    <b>Rechnung Nr:</b> {invoice.get('INVOICE_NR', '')}<br>
                    <b>Kundennummer:</b> {customer.get('CUSTID', '')}<br>
                    <b>Datum:</b> {invoice.get('CREATION_DATE', '')}
                </td>
            </tr>
        </table>
        <h2>Rechnung</h2>
        <p>Sehr geehrte/r {customer.get('FIRST_NAME', '')},<br>
        vielen Dank für Ihren Auftrag, den wir wie folgt in Rechnung stellen.</p>
        <table width="100%" border="1" cellspacing="0" cellpadding="3" style="border-collapse:collapse;">
            <tr style="background:#25722E;color:#fff;">
                <th>Pos.</th>
                <th>Bezeichnung</th>
                <th>Fläche</th>
                <th>Einzelpreis</th>
                <th>Preis</th>
            </tr>
            {pos_rows}
        </table>
        <br>
        <table align="right" class="summary-table">
            <tr><td>Nettobetrag:</td><td align="right">{total_net:.2f} &euro;</td></tr>
            <tr><td>zzgl. MwSt. ({vat:.1f}%):</td><td align="right">{total_vat:.2f} &euro;</td></tr>
            <tr><td><b>Bruttobetrag:</b></td><td align="right"><b>{total_gross:.2f} &euro;</b></td></tr>
        </table>
        <br style="clear:both;">
        <p>Bitte überweisen Sie den offenen Betrag innerhalb von 14 Tagen auf das bekannte Konto.</p>
        <p>Mit freundlichen Grüßen<br>{service_provider.get('PROVIDER_NAME', '')}</p>
        <br>
        <p><b>Geschäftsführer:</b><br>{ceo_rows}</p>
        </body>
        </html>
        """
        return html