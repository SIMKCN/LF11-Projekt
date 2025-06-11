# IMPORT other Packages
import mimetypes
import sqlite3
import subprocess
from datetime import date
import sys
from functools import partial

from xml.dom import minidom
import xml.etree.ElementTree as ET

import os

# IMPORT PyQt6 Packages
from PyQt6.QtWidgets import QMainWindow, QTableView, QHeaderView, QLineEdit, QLabel, QComboBox, \
    QDoubleSpinBox, QPlainTextEdit, QTextBrowser, QTextEdit, QPushButton, QWidget, QDateEdit, \
    QDialog, QFormLayout, QFileDialog, QMessageBox, QVBoxLayout, QProgressDialog, QAbstractItemView
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QPixmap
from PyQt6.QtCore import QModelIndex, Qt, QTimer
from PyQt6 import uic
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView

import config
# IMPORT Functions from local scripts
from database import get_next_primary_key, fetch_all
from validation import *
from config import UI_PATH, DB_PATH, POSITION_DIALOG_PATH, DEBOUNCE_TIME, CACHE_OUTPUT_PATH, IS_AUTHORIZATION_ACTIVE, \
    MIN_LENGTH_EXPORT
from auth.user_management_dialog import UserManagementDialog
from utils import show_error, format_exception, show_info, get_max_permission
from logic import get_service_provider_ceos

from pdfCreation import InvoicePDFBuilder


class InfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("Qt/info_dialog.ui", self)

class PasswordDialog(QDialog):
    def __init__(self, min_length=MIN_LENGTH_EXPORT, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Passwort festlegen")
        self.min_length = min_length
        self.password = None  # Rückgabewert

        self.label1 = QLabel("Passwort:")
        self.input1 = QLineEdit()
        self.input1.setEchoMode(QLineEdit.EchoMode.Password)

        self.label2 = QLabel("Passwort bestätigen:")
        self.input2 = QLineEdit()
        self.input2.setEchoMode(QLineEdit.EchoMode.Password)

        self.button_ok = QPushButton("OK")
        self.button_ok.clicked.connect(self.check_password)

        layout = QVBoxLayout()
        layout.addWidget(self.label1)
        layout.addWidget(self.input1)
        layout.addWidget(self.label2)
        layout.addWidget(self.input2)
        layout.addWidget(self.button_ok)
        self.setLayout(layout)

    def check_password(self):
        pwd1 = self.input1.text()
        pwd2 = self.input2.text()

        if pwd1 != pwd2:
            QMessageBox.warning(self, "Fehler", "Die Passwörter stimmen nicht überein.")
            return

        if len(pwd1) < self.min_length:
            QMessageBox.warning(self, "Fehler", f"Das Passwort muss mindestens {self.min_length} Zeichen lang sein.")
            return

        self.password = pwd1
        self.accept()  # Dialog schließen

    def get_password(self):
        return self.password

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
            "Bezeichnung": self.le_name.text(),
            "Beschreibung": self.te_description.toPlainText(),
            "Fläche": self.sb_area.value(),
            "Einzelpreis": self.sb_unit_price.value(),
        }

# Class :QMainWindow: for the whole UI functionality
class MainWindow(QMainWindow):
    def __init__(self, user_id=None, username=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user_id = user_id
        self.current_username = username
        try:
            # load UI file
            uic.loadUi(UI_PATH, self)
        except Exception as e:
            print("UI Loading Error", f"Could not load UI file.\nError: {str(e)}")
            sys.exit(1)
        if username:
            self.setWindowTitle(f"{self.windowTitle()} - angemeldet als {username}")

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
            }
            # Entferne tab_rechnungen und tab_positionen aus relationships!
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
        self.tv_detail_positionen = self.findChild(QTableView, "tv_detail_positionen")
        os.makedirs(CACHE_OUTPUT_PATH, exist_ok=True)


        # PDF Dokument & Viewer erstellen
        self.pdf_document = QPdfDocument(self)
        self.pdf_view = QPdfView(self)
        self.pdf_view.setDocument(self.pdf_document)
        self.pdf_view.setMinimumSize(400, 600)  # Optional: Mindestgröße setzen
        self.pdf_view.show()  # initial ausblenden
        self.create_missing_invoice_pdfs()

        # PDF-Viewer rechts im Rechnungen-Tab platzieren
        rechnungen_tab = self.findChild(QWidget, "tab_rechnungen")
        main_layout = rechnungen_tab.layout()  # Das ist das QHBoxLayout layoutTabRechnungenMain
        if main_layout is not None:
            main_layout.addWidget(self.pdf_view)

        # Connect Signal for Tab Change
        self.tabWidget.currentChanged.connect(self.on_tab_changed)
        self.tabWidget.currentChanged.connect(self.update_export_button_state)
        # set correct on start
        self.on_tab_changed(self.tabWidget.currentIndex())

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
            btn_hinzufuegen.clicked.connect(self.on_eintrag_hinzufuegen_clicked)

        # Connect Signal for Click on 'btn_drucken'
        btn_drucken = self.findChild(QPushButton, "btn_drucken")
        if btn_drucken:
            btn_drucken.clicked.connect(self.print_invoice)

        # Connect Signal for Click on 'btn_eintrag_loeschen'
        btn_eintrag_loeschen = self.findChild(QPushButton, "btn_eintrag_loeschen")
        if btn_eintrag_loeschen:
            btn_eintrag_loeschen.clicked.connect(self.on_entry_delete)

        # Connect Signal for Click on 'btn_rechnung_exportieren'
        self.btn_rechnung_exportieren = self.findChild(QPushButton, "btn_rechnung_exportieren")
        if self.btn_rechnung_exportieren:
            self.btn_rechnung_exportieren.clicked.connect(self.on_rechnung_exportieren_clicked)

        # Connect Signal for Click on 'btn_drucken'
        self.btn_drucken = self.findChild(QPushButton, "btn_drucken")
        if self.btn_drucken:
            self.btn_drucken.clicked.connect(self.on_drucken_clicked)

        # Connect Signal for Click on 'btn_close_rechnung_hinzufuegen'
        self.btn_close_form = self.findChild(QPushButton, "btn_close_rechnung_hinzufuegen")
        if self.btn_close_form:
            self.btn_close_form.clicked.connect(self.pdf_view.show)

        # Connect Signal for Click on 'btn_nutzer_verwalten'
        self.btn_nutzer_verwalten = self.findChild(QPushButton, "btn_nutzer_verwalten")
        if self.btn_nutzer_verwalten:
            self.btn_nutzer_verwalten.clicked.connect(self.open_user_management)

        # Connect Signal for Click on 'btn_nutzer_verwalten'
        self.btn_info = self.findChild(QPushButton, "btn_info")
        if self.btn_info:
            self.btn_info.clicked.connect(self.show_info_dialog)

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

        self.btn_drucken.setEnabled(False)
        self.btn_nutzer_verwalten.setEnabled(False)
        self.btn_rechnung_exportieren.setEnabled(False)
        self.tb_search_entries.setEnabled(False)
        self.btn_eintrag_hinzufuegen.setEnabled(False)
        self.btn_eintrag_speichern.setEnabled(False)
        self.btn_eintrag_loeschen.setEnabled(False)

        # RECHTEPRÜFUNG
        if get_max_permission(self.current_user_id) >= 1:
            self.tb_search_entries.setEnabled(True)
            self.btn_rechnung_exportieren.setEnabled(True)
            self.btn_drucken.setEnabled(True)

        if get_max_permission(self.current_user_id) >= 2:
            self.btn_eintrag_hinzufuegen.setEnabled(True)
            self.btn_eintrag_speichern.setEnabled(True)

        if get_max_permission(self.current_user_id) >= 3:
            self.btn_eintrag_loeschen.setEnabled(True)

        if get_max_permission(self.current_user_id) >= 100:
            self.btn_nutzer_verwalten.setEnabled(True)


    # Initializes all table views by loading data from corresponding database views
    def init_tables(self):
        # Zuerst alle TableViews leeren
        for table_view_name in self.table_mapping:
            table_view = self.findChild(QTableView, table_view_name)
            if table_view:
                empty_model = QStandardItemModel()
                table_view.setModel(empty_model)
        # Dann wie bisher alle Tabellen neu laden
        for table_view_name, db_view_name in self.table_mapping.items():
            table_view = self.findChild(QTableView, table_view_name)
            if table_view:
                self.load_table(table_view, db_view_name)

    # Loads data into a QTableView from a database view.
    def load_table(self, table_view: QTableView, db_view: str):
        if not get_max_permission(self.current_user_id) >= 1:
            table_view.setModel(QStandardItemModel())
            return

        try:
            data, columns = fetch_all(f"SELECT * FROM {db_view}")
        except Exception as e:
            error_message = f"Error while loading {db_view}: {format_exception(e)}"
            print(error_message)
            table_view.setModel(QStandardItemModel())
            return

        try:
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(columns)
            for row in data:
                items = [QStandardItem(str(cell)) for cell in row]
                # Erste Spalte rechtsbündig
                if items:
                    items[0].setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                for item in items:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                model.appendRow(items)
            # Alle Spalten: Breite automatisch an Inhalt und Header anpassen
            header = table_view.horizontalHeader()
            for col in range(header.count()):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
            # (Optional: danach Stretch für letzte Spalte, falls du willst:)
            # header.setStretchLastSection(True)

            table_view.setModel(model)
            self.adjust_tableview_columns(table_view)
            table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)

            self.connect_row_selected_signal(table_view, db_view)
        except Exception as e:
            error_message = f"Error while populating table {db_view}: {format_exception(e)}"
            print(error_message)

    # Clears and enables all form fields
    def clear_and_enable_form_fields(self):
        self.pdf_view.hide()
        try:
            self.temp_positionen = []
            self.load_all_and_temp_positions_for_rechnungsformular()
            self.findChild(QLabel, "lbl_dienstleister_logo").clear()
            self.btn_logo_upload.setEnabled(True)
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

    # Handles the event when a row is selected in a table view
    def on_row_selected(self, current: QModelIndex, previous: QModelIndex, db_view: str, table_view: QTableView):
        if not current.isValid():
            # Detailansicht leeren, wenn keine Auswahl
            if table_view.objectName() == "tv_positionen" and self.tv_detail_positionen:
                self.tv_detail_positionen.setModel(QStandardItemModel())
            return

        try:
            row_id = current.sibling(current.row(), 0).data()
            if table_view.objectName() == "tv_positionen":
                self.load_positions_invoices(row_id)
            elif table_view.objectName() in self.detail_mapping:
                if table_view.objectName() == "tv_rechnungen":
                    # Falls du weiterhin Rechnungspositionen anzeigen willst
                    self.load_invoice_positions(row_id)
                    self.create_and_show_invoice_pdf(row_id)
                elif table_view.objectName() == "tv_dienstleister":
                    self.load_service_provider_details(row_id)
            self.update_form(current, table_view)
        except Exception as e:
            error_message = f"Error handling row selection in {db_view}: {format_exception(e)}"
            print(error_message)

    # Updates the current form and lbl_eintrag_erstellt_datum with the selected row's data
    def update_form(self, current: QModelIndex, table_view: QTableView):
        model = current.model()
        if not model:
            return

        try:
            # Speziell: CEOs für Dienstleister immer korrekt aus DB holen!
            if table_view.objectName() == "tv_dienstleister":
                ust_idnr = current.sibling(current.row(), 0).data()
                ceo_widget = self.findChild(QLineEdit, "tv_dienstleister_CEOS")
                self.btn_logo_upload.setDisabled(True)
                if ceo_widget:
                    ceo_names = []
                    try:
                        with sqlite3.connect(DB_PATH) as conn:
                            cur = conn.cursor()
                            cur.execute("""
                                SELECT CEO.CEO_NAME
                                FROM CEO
                                JOIN REF_LABOR_COST ON CEO.ST_NR = REF_LABOR_COST.FK_ST_NR
                                WHERE REF_LABOR_COST.FK_UST_IDNR = ?
                            """, (ust_idnr,))
                            ceo_names = [row[0] for row in cur.fetchall()]
                    except Exception as e:
                        ceo_names = []
                    ceo_widget.setText(", ".join(ceo_names))
                    ceo_widget.setEnabled(False)

            for col in range(model.columnCount()):
                column_name = model.headerData(col, Qt.Orientation.Horizontal)
                value = current.sibling(current.row(), col).data()
                widget = self.findChild((QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit),
                                        f"{table_view.objectName()}_{column_name}")

                # CEOs werden schon oben gesetzt!
                if table_view.objectName() == "tv_dienstleister" and column_name == "CEOS" and isinstance(widget,
                                                                                                          QLineEdit):
                    continue

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

        except Exception as e:
            error_message = f"Error updating form : {format_exception(e)}"
            print(error_message)

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
            self.tv_detail_dienstleister.setModel(model)
            self.adjust_tableview_columns(self.tv_detail_dienstleister)
            self.tv_detail_dienstleister.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            self.tv_detail_dienstleister.setSelectionMode(QTableView.SelectionMode.SingleSelection)
            self.show_service_provider_logo(service_provider_id)
        except Exception as e:
            error_message = f"Error while loading CEO details: {format_exception(e)}"
            print(error_message)

    # Loads all positions for selected row from INVOICE_ID
    def load_invoice_positions(self, invoice_id: str):
        try:
            # Alle Positionen zu dieser Rechnung laden
            query = """
                SELECT
                    p.POS_ID AS PositionsID,
                    p.CREATION_DATE AS "Erstellungsdatum Position",
                    p.NAME AS Bezeichnung,
                    p.DESCRIPTION AS Beschreibung,
                    p.UNIT_PRICE AS Einzelpreis,
                    p.AREA AS Flaeche
                FROM REF_INVOICES_POSITIONS ref
                JOIN POSITIONS p ON ref.FK_POSITIONS_POS_ID = p.POS_ID
                WHERE ref.FK_INVOICES_INVOICE_NR = ?
            """
            data, columns = fetch_all(query, (invoice_id,))
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(columns)
            for row in data:
                items = [QStandardItem(str(cell)) for cell in row]
                for item in items:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                model.appendRow(items)
            self.tv_detail_rechnungen.setModel(model)
            self.adjust_tableview_columns(self.tv_detail_rechnungen)
            self.tv_detail_rechnungen.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            self.tv_detail_rechnungen.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        except Exception as e:
            error_message = f"Error while loading invoice positions: {format_exception(e)}"
            print(error_message)

    def load_positions_invoices(self, row_id):
        try:
            query = """
                SELECT i.INVOICE_NR AS Rechnungsnummer,
                       i.CREATION_DATE AS Rechnungsdatum,
                       i.FK_CUSTID AS Kundennummer,
                       i.FK_UST_IDNR AS Dienstleister,
                       i.LABOR_COST AS Lohnkosten
                FROM REF_INVOICES_POSITIONS ref
                JOIN INVOICES i ON ref.FK_INVOICES_INVOICE_NR = i.INVOICE_NR
                WHERE ref.FK_POSITIONS_POS_ID = ?
            """
            data, columns = fetch_all(query, (row_id,))
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(columns)
            for row in data:
                items = [QStandardItem(str(cell)) for cell in row]
                for item in items:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                model.appendRow(items)

            if self.tv_detail_positionen:
                self.tv_detail_positionen.setModel(model)
                self.adjust_tableview_columns(self.tv_detail_positionen)
                self.tv_detail_positionen.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
                self.tv_detail_positionen.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        except Exception as e:
            print("Fehler beim Laden der Rechnungen", str(e))

    # Updates 'lbl_search_for' with corresponding tab name
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

    # Saves and commits the data from form current form into DB
    def on_save_entry(self):
        if not get_max_permission(self.current_user_id) >= 2:
            return

        current_tab = self.tabWidget.currentWidget().objectName()
        main_fields = self.tab_field_mapping.get(current_tab, [])
        rels = self.relationships.get(current_tab, {})

        rel_data = {}
        try:
            if getattr(config, "IS_VALIDATION_ACTIVE", False):
                # Validierung Hauptfelder
                valid, main_data, error = self.validate_and_collect_fields(main_fields, current_tab)
                if not valid:
                    show_error(self, "Validierungsfehler", error)
                    return

                # Validierung Relationen
                for rel, rel_info in rels.items():
                    fields = rel_info["fields"]
                    valid, sub_data, error = self.validate_and_collect_fields(fields, current_tab)
                    if not valid:
                        show_error(self, "Validierungsfehler", error)
                        return
                    rel_data[rel] = sub_data
            else:
                # Felder einfach einsammeln (ohne Prüfung)
                main_data = {}
                for field_name in main_fields:
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
                    main_data[field_name] = value

                for rel, rel_info in rels.items():
                    fields = rel_info["fields"]
                    sub_data = {}
                    for field_name in fields:
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
                        sub_data[field_name] = value
                    rel_data[rel] = sub_data

            def parse_float(val):
                if val is None:
                    return 0.0
                if isinstance(val, (float, int)):
                    return float(val)
                if isinstance(val, str):
                    val = val.strip().replace(",", ".")
                    if val == "":
                        return 0.0
                    try:
                        return float(val)
                    except Exception:
                        return 0.0
                return 0.0

            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()

                if current_tab == "tab_rechnungen":
                    # Kundenauswahl prüfen
                    kunde_index = self.tv_rechnungen_form_kunde.currentIndex()
                    if not kunde_index.isValid():
                        show_error(self, "Kein Kunde ausgewählt", "Bitte wähle einen Kunden aus!")
                        return
                    main_data["FK_CUSTID"] = kunde_index.sibling(kunde_index.row(), 0).data()
                    # Dienstleisterauswahl prüfen
                    dl_index = self.tv_rechnungen_form_dienstleister.currentIndex()
                    if not dl_index.isValid():
                        show_error(self, "Kein Dienstleister ausgewählt", "Bitte wähle einen Dienstleister aus!")
                        return
                    main_data["FK_UST_IDNR"] = dl_index.sibling(dl_index.row(), 0).data()
                    # Rechnung speichern
                    cur.execute(
                        "INSERT INTO INVOICES (INVOICE_NR, CREATION_DATE, FK_CUSTID, FK_UST_IDNR, LABOR_COST, VAT_RATE_LABOR, VAT_RATE_POSITIONS) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            main_data.get("tb_rechnungsnummer", ""),
                            main_data.get("de_erstellungsdatum", ""),
                            main_data.get("FK_CUSTID", ""),
                            main_data.get("FK_UST_IDNR", ""),
                            parse_float(main_data.get("dsb_lohnkosten")),
                            parse_float(main_data.get("dsb_mwst_lohnkosten")),
                            parse_float(main_data.get("dsb_mwst_positionen")),
                        )
                    )

                    selected_indexes = self.tv_rechnungen_form_positionen.selectionModel().selectedRows()
                    for idx in selected_indexes:
                        pos_id = idx.sibling(idx.row(), 0).data()
                        # Neue Position ("NEU-x")?
                        if isinstance(pos_id, str) and pos_id.startswith("NEU-"):
                            temp_index = int(pos_id.split("-")[1]) - 1
                            if temp_index < 0 or temp_index >= len(self.temp_positionen):
                                print("FEHLER: temp_index out of range!", temp_index, self.temp_positionen)
                                continue
                            pos = self.temp_positionen[temp_index]
                            area_raw = pos.get("AREA", 0)
                            unit_price_raw = pos.get("UNIT_PRICE", 0)
                            area = parse_float(area_raw)
                            unit_price = parse_float(unit_price_raw)
                            # Neue Position schreiben
                            cur.execute(
                                "INSERT INTO POSITIONS (CREATION_DATE, DESCRIPTION, AREA, UNIT_PRICE, NAME) VALUES (?, ?, ?, ?, ?)",
                                (
                                    main_data.get("de_erstellungsdatum", ""),
                                    pos.get("DESCRIPTION", ""),
                                    area,
                                    unit_price,
                                    pos.get("NAME", ""),
                                )
                            )
                            new_pos_id = cur.lastrowid
                            # Verknüpfung mit Rechnung speichern
                            cur.execute(
                                "INSERT INTO REF_INVOICES_POSITIONS (FK_POSITIONS_POS_ID, FK_INVOICES_INVOICE_NR) VALUES (?, ?)",
                                (new_pos_id, main_data.get("tb_rechnungsnummer", ""))
                            )
                        else:
                            # Bestehende Position: nur Verknüpfung speichern
                            try:
                                cur.execute(
                                    "INSERT INTO REF_INVOICES_POSITIONS (FK_POSITIONS_POS_ID, FK_INVOICES_INVOICE_NR) VALUES (?, ?)",
                                    (int(pos_id), main_data.get("tb_rechnungsnummer", ""))
                                )
                            except Exception as e:
                                print("FEHLER bei existierender Position:", pos_id, e)
                                continue

                    # Commit
                    conn.commit()
                    self.temp_positionen = []
                    self.load_all_and_temp_positions_for_rechnungsformular()
                    self.create_and_show_invoice_pdf(main_data.get("tb_rechnungsnummer", ""))

                elif current_tab == "tab_kunden":
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

                    cur.execute(
                        "INSERT INTO CUSTOMERS (CUSTID, FIRST_NAME, LAST_NAME, GENDER,CREATION_DATE, FK_ADDRESS_ID) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            main_data.get("tv_kunden_Kundennummer", ""),
                            main_data.get("tv_kunden_Vorname", ""),
                            main_data.get("tv_kunden_Nachname", ""),
                            main_data.get("tv_kunden_Geschlecht", ""),
                            date.today().strftime("%d.%m.%Y"),
                            address_id
                        )
                    )

                elif current_tab == "tab_dienstleister":
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
                    logo_id = None
                    if (getattr(self, "file_name", None) and getattr(self, "logo_data", None) and len(
                            self.logo_data) > 0):
                        logo_file_name = self.file_name
                        logo_data = self.logo_data
                        file_type = getattr(self, "mime_type", "") or ""
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
                    cur.execute(
                        "INSERT INTO SERVICE_PROVIDER (UST_IDNR, MOBILTELNR, PROVIDER_NAME, FAXNR, WEBSITE, EMAIL, TELNR, CREATION_DATE, FK_ADDRESS_ID, FK_LOGO_ID) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            main_data.get("tv_dienstleister_UStIdNr", ""),
                            main_data.get("tv_dienstleister_Mobiltelefonnummer", ""),
                            main_data.get("tv_dienstleister_Unternehmensname", ""),
                            main_data.get("tv_dienstleister_Faxnummer", ""),
                            main_data.get("tv_dienstleister_Webseite", ""),
                            main_data.get("tv_dienstleister_Email", ""),
                            main_data.get("tv_dienstleister_Telefonnummer", ""),
                            date.today().strftime("%d.%m.%Y"),
                            address_id,
                            logo_id
                        )
                    )
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
                            (iban, bic, main_data.get("tv_dienstleister_UStIdNr", ""))
                        )
                    ceo_names_text = main_data.get("tv_dienstleister_CEOS", "")
                    ceo_names = [n.strip() for n in ceo_names_text.split(",") if n.strip()]

                    # Prüfe auf doppelte Namen
                    unique_names = set()
                    duplicate_names = set()
                    for name in ceo_names:
                        if name in unique_names:
                            duplicate_names.add(name)
                        else:
                            unique_names.add(name)

                    if duplicate_names:
                        # Es gibt doppelte Namen, nur EIN Dialog für den jeweiligen Namen anzeigen
                        show_error(self, "Fehler",
                                   f"HALLO ???!! Bist du dumm? Was gibst du zweimal den selben Namen ein? \n"
                                   f"Verfatz dich!")
                        ceo_names = list(unique_names)

                    while ceo_names:
                        ceo_dlg = CEOStNrDialog(ceo_names, self)
                        if ceo_dlg.exec() != QDialog.DialogCode.Accepted:
                            show_error(self, "Abbruch", "Speichern ohne Steuernummern nicht möglich.")
                            return
                        ceo_stnr_map = ceo_dlg.get_ceo_st_numbers()
                        conflict = False
                        ceo_inserts = []
                        ref_inserts = []
                        used_steuernrs = set()

                        for ceo_name, st_nr in ceo_stnr_map.items():
                            if not ceo_name or not st_nr:
                                show_error(self, "Fehler", "Alle Felder müssen ausgefüllt werden!")
                                conflict = True
                                break
                            if st_nr in used_steuernrs:
                                show_error(self, "Fehler",
                                           f"Die Steuernummer {st_nr} wurde mehrmals eingegeben. Jede Steuernummer darf nur einmal verwendet werden.")
                                conflict = True
                                break
                            used_steuernrs.add(st_nr)
                            try:
                                cur.execute("SELECT 1 FROM CEO WHERE ST_NR=? AND CEO_NAME=?", (st_nr, ceo_name))
                                row = cur.fetchone()
                            except Exception as e:
                                show_error(self, "Fehler beim Datenbankzugriff",
                                           f"Fehler bei Prüfung der Steuernummer {st_nr}: {e}")
                                conflict = True
                                break
                            if row is None:
                                ceo_inserts.append((st_nr, ceo_name))

                            try:
                                cur.execute(
                                    "SELECT COUNT(*) FROM REF_LABOR_COST WHERE FK_ST_NR=? AND FK_UST_IDNR=?",
                                    (st_nr, main_data.get("tv_dienstleister_UStIdNr", ""))
                                )
                                if cur.fetchone()[0] == 0:
                                    ref_inserts.append((st_nr, main_data.get("tv_dienstleister_UStIdNr", "")))
                            except Exception as e:
                                show_error(self, "Fehler beim Datenbankzugriff",
                                           f"Fehler bei Prüfung der Zuordnung für Steuernummer {st_nr}: {e}")
                                conflict = True
                                break

                        if conflict:
                            continue

                        try:
                            for st_nr, ceo_name in ceo_inserts:
                                cur.execute("INSERT INTO CEO (ST_NR, CEO_NAME) VALUES (?, ?)", (st_nr, ceo_name))
                            for st_nr, ust_idnr in ref_inserts:
                                cur.execute(
                                    "INSERT INTO REF_LABOR_COST (FK_ST_NR, FK_UST_IDNR) VALUES (?, ?)",
                                    (st_nr, ust_idnr)
                                )
                        except Exception as e:
                            print("Fehler beim Speichern",
                                  f"Beim Speichern der CEO-Daten ist ein Fehler aufgetreten: {e}")
                            return

                        break

                elif current_tab == "tab_positionen":
                    cur.execute(
                        "INSERT INTO POSITIONS (NAME, DESCRIPTION, AREA, UNIT_PRICE, CREATION_DATE) VALUES (?, ?, ?, ?, ?)",
                        (
                            main_data.get("tv_positionen_Bezeichnung", ""),
                            main_data.get("tv_positionen_Beschreibung", ""),
                            main_data.get("tv_positionen_Flaeche", 0.0),
                            main_data.get("tv_positionen_Einzelpreis", 0.0),
                            date.today().strftime("%d.%m.%Y")
                        )
                    )
                    pos_id = cur.lastrowid

                conn.commit()
                self.refresh_tab_table_views()

                self.load_all_and_temp_positions_for_rechnungsformular()
            show_info(self, "Erfolg", "Eintrag erfolgreich gespeichert.")
            self.clear_and_enable_form_fields()
            self.init_tables()
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            show_error(self, "Speicherfehler", str(e))

    # Validates collected data before commiting into DB
    def validate_and_collect_fields(self, field_names, current_tab):
        errors = []
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

            # --- KUNDEN ---
            if current_tab == "tab_kunden":
                if field_name == "tv_kunden_Kundennummer":
                    if value and not validate_kundennummer(value):
                        errors.append("Kundennummer muss zwischen 00001 und 99999 liegen.")
                elif field_name == "tv_kunden_Hausnummer":
                    if not value or not validate_hausnummer(value):
                        errors.append("Hausnummer darf maximal 4 Zeichen lang sein.")
                elif field_name == "tv_kunden_PLZ":
                    if not value or not validate_plz(value):
                        errors.append("PLZ muss 1 bis 7 Zeichen lang sein.")
                elif field_name in ["tv_kunden_Strasse", "tv_kunden_Stadt", "tv_kunden_Land"]:
                    if not value:
                        errors.append(f"{field_name.replace('tv_kunden_', '')} darf nicht leer sein.")
                else:
                    if not value:
                        errors.append(f"{field_name.replace('tv_kunden_', '')} darf nicht leer sein.")
                data_map[field_name] = value

            # --- DIENSTLEISTER ---
            elif current_tab == "tab_dienstleister":
                if field_name == "tv_dienstleister_UStIdNr":
                    if not value or not validate_ustidnr(value):
                        errors.append("USt-IdNr. darf maximal 11 Zeichen lang sein.")
                elif field_name == "tv_dienstleister_Hausnummer":
                    if not value or not validate_hausnummer(value):
                        errors.append("Hausnummer darf maximal 4 Zeichen lang sein.")
                elif field_name == "tv_dienstleister_PLZ":
                    if not value or not validate_plz(value):
                        errors.append("PLZ muss 1 bis 7 Zeichen lang sein.")
                elif field_name == "tv_dienstleister_Email":
                    if value and not validate_email(value):
                        errors.append("Ungültige E-Mail-Adresse.")
                elif field_name == "tv_dienstleister_Telefonnummer":
                    # Wert immer speichern
                    data_map[field_name] = value
                    continue  # Prüfung später zentral
                elif field_name == "tv_dienstleister_Mobiltelefonnummer":
                    # Wert immer speichern
                    data_map[field_name] = value
                    continue  # Prüfung später zentral
                elif field_name == "tv_dienstleister_BIC":
                    if value and not validate_bic(value):
                        errors.append("BIC darf maximal 12 Zeichen lang sein.")
                elif field_name == "tv_dienstleister_IBAN":
                    if value and not validate_iban(value):
                        errors.append("IBAN darf maximal 22 Zeichen lang sein.")
                elif field_name == "tv_dienstleister_Faxnummer":
                    if value:
                        if not validate_telefonnummer(value):
                            errors.append("Faxnummer ist ungültig.")
                elif field_name in ["tv_dienstleister_Strasse", "tv_dienstleister_Stadt", "tv_dienstleister_Land",
                                    "tv_dienstleister_Unternehmensname"]:
                    if not value:
                        errors.append(f"{field_name.replace('tv_dienstleister_', '')} darf nicht leer sein.")
                else:
                    if not value and field_name not in ["tv_dienstleister_Faxnummer", "tv_dienstleister_Webseite",
                                                        "tv_dienstleister_Logo"]:
                        errors.append(f"{field_name.replace('tv_dienstleister_', '')} darf nicht leer sein.")
                data_map[field_name] = value

            # --- POSITIONEN ---
            elif current_tab == "tab_positionen":
                if field_name == "tv_positionen_PositionsID":
                    if not value or not validate_positionsnummer(value):
                        errors.append("Positionsnummer muss eine fortlaufende Zahl ab 0 sein.")
                elif field_name == "tv_positionen_Beschreibung":
                    if value and not validate_beschreibung(value):
                        errors.append("Beschreibung darf maximal 1000 Zeichen lang sein.")
                elif field_name in ["tv_positionen_Bezeichnung", "tv_positionen_Einzelpreis", "tv_positionen_Flaeche"]:
                    if not value:
                        errors.append(f"{field_name.replace('tv_positionen_', '')} darf nicht leer sein.")
                data_map[field_name] = value

            # --- RECHNUNG ---
            elif current_tab == "tab_rechnungen":
                if field_name == "tb_rechnungsnummer":
                    if not value or not validate_kundennummer(value):
                        errors.append("Rechnungsnummer muss zwischen 00001 und 99999 liegen.")
                elif field_name == "de_erstellungsdatum":
                    if not value:
                        errors.append("Erstellungsdatum muss gesetzt sein.")
                elif field_name in ["dsb_mwst_lohnkosten", "dsb_mwst_positionen"]:
                    if value and not validate_mwst(value):
                        errors.append("MwSt. muss zwischen 0 und 100 liegen.")
                elif field_name == "dsb_lohnkosten":
                    try:
                        if value and float(value) > 0 and not value:
                            errors.append("Lohnkosten müssen ausgefüllt werden, wenn sie größer als 0 sind.")
                    except:
                        errors.append("Lohnkosten müssen eine Zahl sein.")
                else:
                    if not value:
                        errors.append(f"{field_name} darf nicht leer sein.")
                data_map[field_name] = value
            else:
                if not value:
                    errors.append(f"{field_name} darf nicht leer sein.")
                data_map[field_name] = value

        # Spezialregel: Telefonnummer ODER Mobiltelefonnummer muss vorhanden sein, aber beide dürfen auch ausgefüllt sein
        if current_tab == "tab_dienstleister":
            tel = data_map.get("tv_dienstleister_Telefonnummer", "")
            mobil = data_map.get("tv_dienstleister_Mobiltelefonnummer", "")
            if tel is None and mobil is None:
                errors.append("Mindestens eine Telefonnummer oder Mobiltelefonnummer muss ausgefüllt werden.")

        return (len(errors) == 0), data_map, "\n".join(errors)

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
                self.adjust_tableview_columns(self.tv_rechnungen_form_kunde)
                self.tv_rechnungen_form_kunde.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
                self.tv_rechnungen_form_kunde.setSelectionMode(QTableView.SelectionMode.SingleSelection)
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
                self.adjust_tableview_columns(self.tv_rechnungen_form_dienstleister)
                self.tv_rechnungen_form_dienstleister.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
                self.tv_rechnungen_form_dienstleister.setSelectionMode(QTableView.SelectionMode.SingleSelection)
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

    import sqlite3

    def on_dienstleister_selected(self, selected, deselected):
        if not selected.indexes():
            self.selected_dienstleister_id = None
            # Feld leeren und aktivieren
            self.tv_dienstleister_CEOS.setText("")
            self.tv_dienstleister_CEOS.setDisabled(False)
            return

        index = selected.indexes()[0]
        model = self.tv_dienstleister.model()
        if not model:
            self.selected_dienstleister_id = None
            self.tv_dienstleister_CEOS.setText("")
            self.tv_dienstleister_CEOS.setDisabled(False)
            return

        self.selected_dienstleister_id = model.item(index.row(), 0).text()

        # Geschäftsführer aus der DB laden
        ceo_names = []
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT CEO.CEO_NAME
                    FROM CEO
                    JOIN REF_LABOR_COST ON CEO.ST_NR = REF_LABOR_COST.FK_ST_NR
                    WHERE REF_LABOR_COST.FK_UST_IDNR = ?
                """, (self.selected_dienstleister_id,))
                ceo_names = [row[0] for row in cur.fetchall()]
        except Exception as e:
            show_error(self, "Fehler", f"Geschäftsführer konnten nicht geladen werden: {e}")

        # Feld befüllen und deaktivieren
        self.tv_dienstleister_CEOS.setText(", ".join(ceo_names))
        self.tv_dienstleister_CEOS.setDisabled(True)

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
        self.adjust_tableview_columns(self.tv_rechnungen_form_positionen)
        self.tv_rechnungen_form_positionen.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.tv_rechnungen_form_positionen.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

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
                show_error(self, "Fehler", "Bitte eine Bezeichnung angeben!")
                return
            # Rechnungsnummer für spätere Speicherung merken (optional für Validierung)
            rechnungsnummer_feld = self.findChild(QLineEdit, "tb_rechnungsnummer")
            rechnungsnummer = rechnungsnummer_feld.text() if rechnungsnummer_feld else ""
            if not rechnungsnummer:
                show_error(self, "Fehler", "Bitte zuerst eine Rechnungsnummer eintragen!")
                return
            pos_data["FK_INVOICE_NR"] = rechnungsnummer
            self.temp_positionen.append(pos_data)
            self.load_all_and_temp_positions_for_rechnungsformular()

    from PyQt6.QtWidgets import QMessageBox

    def on_entry_delete(self):
        """
        Löscht je nach Tab:
        - Rechnungen: Warnung, m:n-Relationen und Rechnung selbst.
        - Dienstleister: Warnung mit Zählung, löscht zugehörige Rechnungen inkl. m:n-Relationen, Dienstleister, Adresse, ACCOUNTS, REF_LABOR_COST. BANK und CEO bleiben.
        - Kunden: Warnung mit Zählung, löscht zugehörige Rechnungen inkl. m:n-Relationen, Kunde, Adresse.
        - Positionen: Warnung mit Zählung, löscht zugehörige Rechnungen inkl. m:n-Relationen, Position.
        """
        current_tab = self.tabWidget.currentWidget().objectName()
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()

                if current_tab == "tab_rechnungen":
                    idx_rechnung = self.tv_rechnungen.currentIndex()
                    if not idx_rechnung.isValid():
                        show_error(self, "Nichts ausgewählt!", "Bitte wählen Sie eine Rechnung aus!")
                        return
                    invoice_id = idx_rechnung.sibling(idx_rechnung.row(), 0).data()
                    reply = QMessageBox.question(
                        self,
                        "Rechnung löschen",
                        f"Möchten Sie die Rechnung {invoice_id} wirklich löschen?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return

                    cur.execute("DELETE FROM REF_INVOICES_POSITIONS WHERE FK_INVOICES_INVOICE_NR=?", (invoice_id,))
                    cur.execute("DELETE FROM INVOICES WHERE INVOICE_NR=?", (invoice_id,))
                    conn.commit()
                    show_info(self, "Erfolg", f"Rechnung {invoice_id} wurde gelöscht.")
                    self.refresh_tab_table_views()
                    return

                elif current_tab == "tab_dienstleister":
                    idx = self.tv_dienstleister.currentIndex()
                    if not idx.isValid():
                        show_error(self, "Nichts ausgewählt!", "Bitte wählen Sie einen Dienstleister aus!")
                        return
                    ust_idnr = idx.sibling(idx.row(), 0).data()
                    # Rechnungen zählen
                    cur.execute("SELECT COUNT(*) FROM INVOICES WHERE FK_UST_IDNR=?", (ust_idnr,))
                    rechnungs_anzahl = cur.fetchone()[0]
                    msg = f"Möchten Sie den Dienstleister {ust_idnr} wirklich löschen?\n\n"
                    if rechnungs_anzahl > 0:
                        msg += f"Achtung: Es werden dabei {rechnungs_anzahl} zugehörige Rechnung(en) gelöscht!"
                    else:
                        msg += "Es sind keine Rechnungen mit diesem Dienstleister verknüpft."
                    reply = QMessageBox.question(
                        self,
                        "Dienstleister löschen",
                        msg,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return

                    # Rechnungen löschen
                    cur.execute("SELECT INVOICE_NR FROM INVOICES WHERE FK_UST_IDNR=?", (ust_idnr,))
                    invoice_nrs = [row[0] for row in cur.fetchall()]
                    for invoice_id in invoice_nrs:
                        cur.execute("DELETE FROM REF_INVOICES_POSITIONS WHERE FK_INVOICES_INVOICE_NR=?", (invoice_id,))
                        cur.execute("DELETE FROM INVOICES WHERE INVOICE_NR=?", (invoice_id,))

                    # Accounts löschen
                    cur.execute("DELETE FROM ACCOUNT WHERE FK_UST_IDNR=?", (ust_idnr,))
                    # REF_LABOR_COST löschen
                    cur.execute("DELETE FROM REF_LABOR_COST WHERE FK_UST_IDNR=?", (ust_idnr,))
                    # Adresse zu Dienstleister löschen (erst ID holen)
                    cur.execute("SELECT FK_ADDRESS_ID FROM SERVICE_PROVIDER WHERE UST_IDNR=?", (ust_idnr,))
                    adr_row = cur.fetchone()
                    if adr_row and adr_row[0]:
                        cur.execute("DELETE FROM ADDRESSES WHERE ID=?", (adr_row[0],))
                    # Dienstleister selbst löschen
                    cur.execute("DELETE FROM SERVICE_PROVIDER WHERE UST_IDNR=?", (ust_idnr,))
                    conn.commit()
                    show_info(self, "Erfolg",
                              f"Dienstleister {ust_idnr} wurde gelöscht.")
                    self.refresh_tab_table_views()
                    return

                elif current_tab == "tab_kunden":
                    idx = self.tv_kunden.currentIndex()
                    if not idx.isValid():
                        show_error(self, "Nichts ausgewählt!", "Bitte wählen Sie einen Kunden aus!")
                        return
                    custid = idx.sibling(idx.row(), 0).data()
                    cur.execute("SELECT COUNT(*) FROM INVOICES WHERE FK_CUSTID=?", (custid,))
                    rechnungs_anzahl = cur.fetchone()[0]
                    msg = f"Möchten Sie den Kunden {custid} wirklich löschen?\n\n"
                    if rechnungs_anzahl > 0:
                        msg += f"Achtung: Es werden dabei {rechnungs_anzahl} zugehörige Rechnung(en) gelöscht!"
                    else:
                        msg += "Es sind keine Rechnungen mit diesem Kunden verknüpft."
                    reply = QMessageBox.question(
                        self,
                        "Kunde löschen",
                        msg,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return

                    cur.execute("SELECT INVOICE_NR FROM INVOICES WHERE FK_CUSTID=?", (custid,))
                    invoice_nrs = [row[0] for row in cur.fetchall()]
                    for invoice_id in invoice_nrs:
                        cur.execute("DELETE FROM REF_INVOICES_POSITIONS WHERE FK_INVOICES_INVOICE_NR=?", (invoice_id,))
                        cur.execute("DELETE FROM INVOICES WHERE INVOICE_NR=?", (invoice_id,))
                    # Adresse zu Kunde löschen
                    cur.execute("SELECT FK_ADDRESS_ID FROM CUSTOMERS WHERE CUSTID=?", (custid,))
                    address_row = cur.fetchone()
                    if address_row and address_row[0]:
                        cur.execute("DELETE FROM ADDRESSES WHERE ID=?", (address_row[0],))
                    cur.execute("DELETE FROM CUSTOMERS WHERE CUSTID=?", (custid,))
                    conn.commit()
                    show_info(self, "Erfolg", f"Kunde {custid} wurde gelöscht.")
                    self.refresh_tab_table_views()
                    return

                elif current_tab == "tab_positionen":
                    idx = self.tv_positionen.currentIndex()
                    if not idx.isValid():
                        show_error(self, "Nichts ausgewählt!", "Bitte wählen Sie eine Position aus!")
                        return
                    pos_id = idx.sibling(idx.row(), 0).data()
                    cur.execute("SELECT COUNT(*) FROM REF_INVOICES_POSITIONS WHERE FK_POSITIONS_POS_ID=?", (pos_id,))
                    rechnungs_anzahl = cur.fetchone()[0]
                    msg = f"Möchtest du die Position {pos_id} wirklich löschen?\n\n"
                    if rechnungs_anzahl > 0:
                        msg += f"Achtung: Es werden dabei {rechnungs_anzahl} zugehörige Rechnung(en) gelöscht!"
                    else:
                        msg += "Es sind keine Rechnungen mit dieser Position verknüpft."
                    reply = QMessageBox.question(
                        self,
                        "Position löschen",
                        msg,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return
                    # Alle zugehörigen Rechnungen löschen
                    cur.execute("""
                        SELECT i.INVOICE_NR
                        FROM REF_INVOICES_POSITIONS ref
                        JOIN INVOICES i ON ref.FK_INVOICES_INVOICE_NR = i.INVOICE_NR
                        WHERE ref.FK_POSITIONS_POS_ID = ?
                    """, (pos_id,))
                    invoice_nrs = [row[0] for row in cur.fetchall()]
                    for invoice_id in invoice_nrs:
                        cur.execute("DELETE FROM REF_INVOICES_POSITIONS WHERE FK_INVOICES_INVOICE_NR=?", (invoice_id,))
                        cur.execute("DELETE FROM INVOICES WHERE INVOICE_NR=?", (invoice_id,))
                    # Position selbst löschen
                    cur.execute("DELETE FROM POSITIONS WHERE POS_ID=?", (pos_id,))
                    conn.commit()
                    show_info(self, "Erfolg", f"Position {pos_id} wurde gelöscht.")
                    self.refresh_tab_table_views()
                    return

        except Exception as e:
            show_error(self, "Löschfehler", str(e))

    def refresh_tab_table_views(self):
        """
        Aktualisiert alle QTableViews im gesamten Programm,
        unabhängig von Sichtbarkeit oder Einbettung.
        """
        # Optional: Auch die Rechnungsform-Tabellen aktualisieren
        self.init_tv_rechnungen_form_tabellen()

        # Sammle alle QTableViews im Fenster
        all_table_views = self.findChildren(QTableView)
        for table_view in all_table_views:
            obj_name = table_view.objectName()
            db_view = self.table_mapping.get(obj_name)
            if db_view:
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
            self.adjust_tableview_columns(self.tv_rechnungen_form_positionen)
            self.tv_rechnungen_form_positionen.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            self.tv_rechnungen_form_positionen.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
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
                self.connect_row_selected_signal(table_view, db_view_name)
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
        if not get_max_permission(self.current_user_id) >= 1:
            return
        if not self.btn_rechnung_exportieren or not self.btn_drucken:
            return
        if current_tab and current_tab.objectName() == "tab_rechnungen":
            self.btn_rechnung_exportieren.setEnabled(True)
            self.btn_drucken.setEnabled(True)
        else:
            self.btn_rechnung_exportieren.setEnabled(False)
            self.btn_drucken.setEnabled(False)

    def on_rechnung_exportieren_clicked(self):
        idx = self.tv_rechnungen.currentIndex()
        if not idx.isValid():
            show_error(self, "Keine Auswahl", "Bitte zuerst eine Rechnung auswählen!")
            return
        invoice_nr = idx.sibling(idx.row(), 0).data()

        try:
            export_data = self.get_export_data(invoice_nr)

            zip_output_path, _ = QFileDialog.getSaveFileName(
                self,
                "ZIP-Datei speichern unter",
                filter="ZIP-Dateien (*.zip);;Alle Dateien (*)",
                directory="export.zip"
            )
            if not zip_output_path:
                return

            output_dir = os.path.dirname(zip_output_path)
            xml_path = os.path.join(output_dir, "rechnung.xml")
            pdf_path = os.path.join(output_dir, "rechnung.pdf")

            xml_string = self.build_invoice_xml(export_data)

            # Logo aus DB laden (optional)
            fk_logo_id = next(
                (entry["service_provider"]["FK_LOGO_ID"] for entry in export_data if "service_provider" in entry),
                None
            )
            logo_bytes = None
            with sqlite3.connect(DB_PATH) as conn:
                if fk_logo_id:
                    cursor = conn.cursor()
                    cursor.execute("SELECT LOGO_BINARY FROM LOGOS WHERE ID = ?", (fk_logo_id,))
                    result = cursor.fetchone()
                    if result and result[0] is not None:
                        logo_bytes = result[0]

            # XML schreiben
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(xml_string)

            # PDF erzeugen
            builder = InvoicePDFBuilder(xml_string, logo_bytes)
            builder.build(pdf_path)

            # Passwort-Dialog
            dialog = PasswordDialog(min_length=4)
            if not dialog.exec():
                # Abbruch durch Nutzer
                # Temporäre Dateien gleich wieder löschen
                for tmpf in (xml_path, pdf_path):
                    if os.path.exists(tmpf):
                        os.remove(tmpf)
                return
            passwort = dialog.get_password()

            import pyzipper
            with pyzipper.AESZipFile(zip_output_path,
                                     'w',
                                     compression=pyzipper.ZIP_LZMA,
                                     encryption=pyzipper.WZ_AES) as zip_file:
                zip_file.setpassword(passwort.encode("utf-8"))
                files_to_add = [
                    ("rechnung.xml", xml_path),
                    ("rechnung.pdf", pdf_path)
                ]
                for arcname, filepath in files_to_add:
                    zip_file.write(filepath, arcname=arcname)

            # Temporäre Dateien löschen
            for tmpf in (xml_path, pdf_path):
                if os.path.exists(tmpf):
                    os.remove(tmpf)

            # Explorer-Öffnung anbieten
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Export abgeschlossen")
            msg_box.setText(f"Die Datei wurde erfolgreich gespeichert:\n{zip_output_path}\n\n"
                            "Möchten Sie den Speicherort im Explorer öffnen?")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            result = msg_box.exec()

            if result == QMessageBox.StandardButton.Yes:
                folder = os.path.dirname(zip_output_path)
                if os.name == "nt":
                    # Windows
                    os.startfile(folder)
                elif os.name == "posix":
                    # macOS oder Linux
                    try:
                        if sys.platform == "darwin":
                            subprocess.Popen(["open", folder])
                        else:
                            subprocess.Popen(["xdg-open", folder])
                    except Exception as e:
                        show_error(self, "Fehler", f"Konnte Explorer nicht öffnen: {e}")

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
            self.connect_row_selected_signal(table_view, db_view_name)
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
            "Bilder (*.png *.jpg *.jpeg *.bmp *.svg)"
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

            # === Logo-Vorschau ins Label laden ===
            label = self.findChild(QLabel, "lbl_dienstleister_logo")
            if label and self.logo_data:
                pixmap = QPixmap()
                pixmap.loadFromData(self.logo_data)
                # Skaliere das Bild, damit es in das Label passt
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
            self.selected_files = []
            self.file_path = None
            self.file_name = None
            self.logo_data = None
            self.mime_type = None
            if hasattr(self, "fileListWidget"):
                self.fileListWidget.clear()
            # Label leeren, falls kein Bild gewählt
            label = self.findChild(QLabel, "lbl_dienstleister_logo")
            if label:
                label.clear()

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

    def build_invoice_xml(self, export_data):
        root = ET.Element("invoice_data")

        for entry in export_data:
            for key, value in entry.items():
                section = ET.SubElement(root, key)

                if isinstance(value, list):
                    for item in value:
                        item_el = ET.SubElement(section, key[:-1])  # z. B. ceo aus ceos
                        for sub_key, sub_val in item.items():
                            ET.SubElement(item_el, sub_key).text = str(sub_val)

                elif isinstance(value, dict):
                    for sub_key, sub_val in value.items():
                        ET.SubElement(section, sub_key).text = str(sub_val)

                # Extra-Fall für 'service_provider', falls 'logo_id' als separates Feld übergeben wird
                if key == "service_provider" and isinstance(value, dict):
                    if "logo_id" in value:
                        ET.SubElement(section, "FK_LOGO_ID").text = str(value["logo_id"])

        rough_string = ET.tostring(root, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        xml_string = reparsed.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')

        return xml_string

    def adjust_tableview_columns(self, table_view: QTableView):
        """Setzt erste Spalte rechtsbündig, alle Spalten ResizeToContents, und erste Spalte etwas breiter."""
        model = table_view.model()
        if not model or model.columnCount() == 0:
            return
        # Erste Spalte rechtsbündig
        for row in range(model.rowCount()):
            item = model.item(row, 0)
            if item:
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        # Spaltenbreite anpassen
        header = table_view.horizontalHeader()
        for col in range(header.count()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        table_view.resizeColumnsToContents()
        # Erste Spalte extra breit machen
        current_width = table_view.columnWidth(0)
        table_view.setColumnWidth(0, current_width)

    def print_invoice(self):
        return False

    def show_invoice_pdf(self, pdf_path):
        self.pdf_document.load(pdf_path)
        self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)

    def create_and_show_invoice_pdf(self, invoice_nr):
        export_data = self.get_export_data(invoice_nr)
        xml_string = self.build_invoice_xml(export_data)

        # Logo laden
        fk_logo_id = next(
            (entry["service_provider"].get("FK_LOGO_ID") for entry in export_data if "service_provider" in entry),
            None
        )
        logo_bytes = None
        if fk_logo_id:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT LOGO_BINARY FROM LOGOS WHERE ID = ?", (fk_logo_id,))
                result = cursor.fetchone()
                if result and result[0] is not None:
                    logo_bytes = result[0]

        pdf_path = os.path.join(CACHE_OUTPUT_PATH, f"rechnung_{invoice_nr}.pdf")
        builder = InvoicePDFBuilder(xml_string, logo_bytes)
        builder.build(pdf_path)
        self.show_invoice_pdf(pdf_path)

    def create_missing_invoice_pdfs(self):
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT INVOICE_NR FROM INVOICES")
            all_invoices = [row[0] for row in cur.fetchall()]
        missing = []
        for invoice_nr in all_invoices:
            pdf_path = os.path.join(CACHE_OUTPUT_PATH, f"rechnung_{invoice_nr}.pdf")
            if not os.path.exists(pdf_path):
                missing.append(invoice_nr)
        if not missing:
            return
        progress = QProgressDialog("PDFs werden erstellt...", "Abbrechen", 0, len(missing), self)
        progress.setWindowTitle("Rechnung-PDFs generieren")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        for i, invoice_nr in enumerate(missing, 1):
            if progress.wasCanceled():
                break
            self.create_and_show_invoice_pdf(invoice_nr)
            progress.setValue(i)
        progress.setValue(len(missing))

    def get_export_data(self, invoice_nr):
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

            # Bankverbindung(en) zum Dienstleister
            cur.execute("""
                SELECT acc.IBAN, acc.FK_BANK_ID AS BIC, b.BANK_NAME
                FROM ACCOUNT acc
                JOIN BANK b ON acc.FK_BANK_ID = b.BIC
                WHERE acc.FK_UST_IDNR = (SELECT FK_UST_IDNR FROM INVOICES WHERE INVOICE_NR = ?)
            """, (invoice_nr,))
            accounts_rows = cur.fetchall()
            accounts_columns = [desc[0] for desc in cur.description]

        export_data = [
            {"invoice": dict(zip(invoice_columns, invoice_row)) if invoice_row else {}},
            {"customer": dict(zip(customer_columns, customer_row)) if customer_row else {}},
            {"service_provider": dict(zip(provider_columns, provider_row)) if provider_row else {}},
            {"ceos": [dict(zip(ceos_columns, row)) for row in ceos_rows]},
            {"positions": [dict(zip(positions_columns, row)) for row in positions_rows]},
            {"accounts": [dict(zip(accounts_columns, row)) for row in accounts_rows]}
        ]
        return export_data

    def on_drucken_clicked(self):
        try:
            idx = self.tv_rechnungen.currentIndex()
            if not idx.isValid():
                show_error(self, "Keine Auswahl", "Bitte zuerst eine Rechnung auswählen!")
                return

            invoice_nr = idx.sibling(idx.row(), 0).data()
            pdf_path = os.path.join(CACHE_OUTPUT_PATH, f"rechnung_{invoice_nr}.pdf")

            if not os.path.exists(pdf_path):
                self.create_and_show_invoice_pdf(invoice_nr)
                print("Pfad exisitert nicht")

            os.startfile(pdf_path, 'open')
        except Exception as e:
            show_error(self, "Fehler beim Drucken", str(e))

    def open_user_management(self):
        # Rechteprüfung nur, wenn aktiviert
        if IS_AUTHORIZATION_ACTIVE:
            if not get_max_permission(self.current_user_id) >= 100:
                return
        dialog = UserManagementDialog(self)
        dialog.exec()

    def connect_row_selected_signal(self, table_view, db_view):
        sel_model = table_view.selectionModel()
        if sel_model is None:
            print("[DEBUG] Kein selectionModel nach setModel!")
            return
        try:
            sel_model.currentChanged.disconnect()
        except Exception:
            pass
        sel_model.currentChanged.connect(partial(self.on_row_selected, db_view=db_view, table_view=table_view))

    def on_eintrag_hinzufuegen_clicked(self):
        if not get_max_permission(self.current_user_id) >= 2:
            self.w_rechnung_hinzufuegen.setVisible(False)
            return
        self.clear_and_enable_form_fields()
        self.dsb_mwst_lohnkosten.setValue(float(config.DEFAULT_MWST))
        self.dsb_mwst_positionen.setValue(float(config.DEFAULT_MWST))

    def show_info_dialog(self):
        dlg = InfoDialog(self)
        dlg.exec()