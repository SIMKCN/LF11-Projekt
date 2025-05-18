# This file contains the MainWindow class for the application
import sqlite3

from PyQt6.QtWidgets import QMainWindow, QTableView, QHeaderView, QLineEdit, QLabel, QMessageBox, QComboBox, \
    QDoubleSpinBox, QPlainTextEdit, QTextBrowser, QTextEdit, QPushButton, QAbstractItemView, QWidget, QDateEdit, QDialog
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
            "tab_kunden": {"field": "tv_kunden_CUSTID", "table": "CUSTOMERS", "pk_col": "CUSTID", "type": "customer"},
            "tab_dienstleister": {"field": "tv_dienstleister_UST_IDNR", "table": "SERVICE_PROVIDER", "pk_col": "UST_IDNR", "type": "service_provider"},
            "tab_positionen": {"field": "tv_positionen_POS_ID", "table": "POSITIONS", "pk_col": "POS_ID", "type": "positions"}
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
                "tv_kunden_CUSTID", "tv_kunden_FIRST_NAME", "tv_kunden_LAST_NAME", "tv_kunden_GENDER"
            ],
            "tab_kunden_address": [
                "tv_kunden_STREET", "tv_kunden_NUMBER", "tv_kunden_CITY", "tv_kunden_PLZ", "tv_kunden_COUNTRY"
            ],
            "tab_dienstleister": [
                "tv_dienstleister_UST_IDNR", "tv_dienstleister_PROVIDER_NAME", "tv_dienstleister_EMAIL",
                "tv_dienstleister_TELNR", "tv_dienstleister_MOBILTELNR", "tv_dienstleister_FAXNR",
                "tv_dienstleister_WEBSITE"
            ],
            "tab_dienstleister_address": [
                "tv_dienstleister_STREET", "tv_dienstleister_NUMBER", "tv_dienstleister_CITY", "tv_dienstleister_COUNTRY",
            ],
            # Konten/BANK werden ggf. als Listeneintrag oder dynamische Felder erfasst
            "tab_rechnungen": [
                "tb_rechnungsnummer", "de_erstellungsdatum", "dsb_lohnkosten", "dsb_mwst_lohnkosten", "dsb_mwst_positionen"
            ],
            "tab_rechnungen_fk": [  # Foreign Keys für Relationen
                "fk_custid", "fk_ust_idnr"
            ],
            "tab_positionen": [
                "tv_positionen_POS_ID", "tv_positionen_NAME", "tv_positionen_DESCRIPTION", "tv_positionen_AREA",
                "tv_positionen_UNIT_PRICE"
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
                    "fields": ["tv_dienstleister_IBAN", "tv_dienstleister_BIC", "tv_dienstleister_BANK_NAME"],  # Passe die Feldnamen an deine GUI an!
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
            self.update_positionen_tableview()
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
                    widget.setCurrentText(str(value) if value is not None else "0,01")
                    widget.setEnabled(False)
                elif isinstance(widget, QDoubleSpinBox):
                    try:
                        widget.setValue(float(value.replace(",", ".")) if value is not None else widget.setValue(0))
                    except (ValueError, TypeError):
                        widget.setValue(0)
                    widget.setEnabled(False)
                elif isinstance(widget, QTextEdit):
                    widget.setText(value if value is not None else "0,04")
                    widget.setEnabled(False)

            eintrag_datum = None
            for col in range(model.columnCount()):
                header = model.headerData(col, Qt.Orientation.Horizontal)
                if header == "CREATION_DATE":
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
        Loads positions for a selected invoice.
        """
        try:
            data = get_invoice_positions(invoice_id)
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["Position ID", "Name", "Description", "Area", "Unit Price"])
            for row in data:
                items = [QStandardItem(str(cell)) for cell in row]
                model.appendRow(items)
            self.tv_detail_rechnungen.setModel(model)
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
                    # Rechnung speichern
                    if "customer" in rel_data:
                        main_data["FK_CUSTID"] = rel_data["customer"].get("fk_custid",
                                                                          None) or self.get_selected_kunde_id()
                    else:
                        main_data["FK_CUSTID"] = self.get_selected_kunde_id()
                        # FK_UST_IDNR
                    if "service_provider" in rel_data:
                        main_data["FK_UST_IDNR"] = rel_data["service_provider"].get("fk_ust_idnr",
                                                                                    None) or self.get_selected_dienstleister_id()
                    else:
                        main_data["FK_UST_IDNR"] = self.get_selected_dienstleister_id()
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
                    # Positionen speichern
                    for pos in self.temp_positionen:
                        cur.execute("SELECT COALESCE(MAX(POS_ID), 0) + 1 FROM POSITIONS")
                        next_pos_id = cur.fetchone()[0]
                        cur.execute(
                            "INSERT INTO POSITIONS (POS_ID, CREATION_DATE, FK_INVOICE_NR, DESCRIPTION, AREA, UNIT_PRICE, NAME) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (
                                next_pos_id,
                                main_data["de_erstellungsdatum"],
                                main_data["tb_rechnungsnummer"],
                                pos.get("DESCRIPTION", ""),
                                pos.get("AREA", 0),
                                pos.get("UNIT_PRICE", 0),
                                pos.get("NAME", ""),
                            )
                        )

                elif current_tab == "tab_kunden":
                    # Adresse speichern und FK holen
                    address_id = None
                    if "address" in rel_data:
                        addr = rel_data["address"]
                        cur.execute(
                            "INSERT INTO ADDRESSES (STREET, NUMBER, CITY, PLZ, COUNTRY, CREATION_DATE) VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                addr.get("tv_kunden_STREET", ""),
                                addr.get("tv_kunden_NUMBER", ""),
                                addr.get("tv_kunden_CITY", ""),
                                addr.get("tv_kunden_PLZ", ""),
                                addr.get("tv_kunden_COUNTRY", ""),
                                date.today().strftime("%d.%m.%Y")
                            )
                        )
                        address_id = cur.lastrowid

                    # Kunde speichern mit ADDRESS_ID als FK
                    cur.execute(
                        "INSERT INTO CUSTOMERS (CUSTID, FIRST_NAME, LAST_NAME, GENDER,CREATION_DATE, FK_ADDRESS_ID) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            main_data["tv_kunden_CUSTID"],
                            main_data["tv_kunden_FIRST_NAME"],
                            main_data["tv_kunden_LAST_NAME"],
                            main_data["tv_kunden_GENDER"],
                            date.today().strftime("%d.%m.%Y"),
                            address_id
                        )
                    )

                conn.commit()

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
            model.setHorizontalHeaderLabels(["UST-IDNR", "Unternehmen"])
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
        model.setHorizontalHeaderLabels(["Name", "Beschreibung", "Fläche", "Stückpreis"])
        for pos in self.temp_positionen:
            items = [
                QStandardItem(str(pos.get("NAME", ""))),
                QStandardItem(str(pos.get("DESCRIPTION", ""))),
                QStandardItem(str(pos.get("AREA", ""))),
                QStandardItem(str(pos.get("UNIT_PRICE", ""))),
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
            self.update_positionen_tableview()