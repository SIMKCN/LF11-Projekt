# This file contains the MainWindow class for the application
import sqlite3

from PyQt6.QtWidgets import QMainWindow, QTableView, QHeaderView, QLineEdit, QLabel, QMessageBox, QComboBox, \
    QDoubleSpinBox, QPlainTextEdit, QTextBrowser, QTextEdit, QPushButton, QAbstractItemView
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6 import uic
from datetime import date
import sys
from database import get_next_primary_key
from config import UI_PATH, DB_PATH
from utils import show_error, format_exception, show_info
from database import fetch_all
from logic import get_ceos_for_service_provider_form, get_service_provider_ceos, get_invoice_positions


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
        # Connect Signal for Tab Change
        self.tabWidget.currentChanged.connect(self.on_tab_changed)
        # set correct on start
        self.on_tab_changed(self.tabWidget.currentIndex())

        self.init_tables()
        self.w_rechnung_hinzufuegen.setVisible(False)
        self.de_erstellungsdatum.setDate(date.today())
        self.showMaximized()

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