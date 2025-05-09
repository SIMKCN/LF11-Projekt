from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtWidgets import QMainWindow, QApplication, QTableView, QHeaderView, QLineEdit, QLabel, QMessageBox, \
    QComboBox, QDoubleSpinBox, QPlainTextEdit, QTextBrowser, QTextEdit, QPushButton
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6 import uic
import sqlite3
import sys
import traceback


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            uic.loadUi("./Qt/main.ui", self)  # Load UI file
        except Exception as e:
            self.show_error("UI Loading Error", f"Could not load UI file.\nError: {str(e)}")
            sys.exit(1)

        # Database configuration
        self.db_path = "rechnungsverwaltung.db"

        # Mapping table views to database views
        self.table_mapping = {
            "tv_rechnungen": "view_invoices_full",
            "tv_dienstleister": "view_service_provider_full",
            "tv_kunden": "view_customers_full",
            "tv_positionen": "view_positions_full",
        }

        # Detail table views for specific tables
        self.detail_mapping = {
            "tv_rechnungen": self.tv_detail_rechnungen,
            "tv_dienstleister": self.tv_detail_dienstleister,
        }

        self.init_tables()

        self.w_rechnung_hinzufuegen.hide()

        # Connect the "Eintrag Hinzufügen (+)" button to clear and enable fields
        btn_hinzufuegen = self.findChild(QPushButton, "btn_eintrag_hinzufuegen")
        if btn_hinzufuegen:
            btn_hinzufuegen.clicked.connect(self.clear_and_enable_form_fields)

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
            print(f"Loading data for table: {db_view}")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {db_view}")
                data = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
        except sqlite3.OperationalError as e:
            error_message = f"Database error while loading {db_view}: {e}"
            print(error_message)
            self.show_error("Database Error", error_message)
            table_view.setModel(QStandardItemModel())  # Clear table view if error occurs
            return
        except Exception as e:
            error_message = f"Unexpected error while loading {db_view}: {e}\n{traceback.format_exc()}"
            print(error_message)
            self.show_error("Unexpected Error", error_message)
            table_view.setModel(QStandardItemModel())
            return

        # Populate the table view
        try:
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(columns)
            for row in data:
                items = [QStandardItem(str(cell)) for cell in row]
                for item in items:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make items read-only
                model.appendRow(items)

            table_view.setModel(model)
            table_view.resizeColumnsToContents()
            table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)

            header = table_view.horizontalHeader()
            for col in range(header.count()):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

            # Connect selection change event
            table_view.selectionModel().currentChanged.connect(
                lambda current, previous: self.on_row_selected(current, db_view, table_view)
            )
        except Exception as e:
            error_message = f"Error while populating table {db_view}: {e}\n{traceback.format_exc()}"
            print(error_message)
            self.show_error("Table Population Error", error_message)

    def clear_and_enable_form_fields(self):
        """
        Clears and enables all form fields on the current tab.
        """
        try:
            # Get a list of all possible form field types
            form_field_types = (QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit, QTextBrowser)

            # Iterate over all child widgets of the main window and process only those within the current tab
            for field in self.findChildren(form_field_types):
                if field.isVisible():  # Ensure the field is part of the current visible tab
                    # Clear the field based on its type
                    if isinstance(field, QLineEdit):
                        field.clear()
                    elif isinstance(field, QComboBox):
                        field.setCurrentIndex(-1)  # Reset to no selection
                    elif isinstance(field, QDoubleSpinBox):
                        field.setValue(0.0)  # Reset to default value
                    elif isinstance(field, (QTextEdit, QPlainTextEdit, QTextBrowser)):
                        field.clear()

                    # Enable the field for editing
                    field.setEnabled(True)

            # Clear the creation date label
            lbl_creation_date = self.findChild(QLabel, "lbl_eintrag_erstellt_datum")
            if lbl_creation_date:
                lbl_creation_date.setText("Erstellt am: N/A")

        except Exception as e:
            error_message = f"Error while clearing and enabling form fields: {e}\n{traceback.format_exc()}"
            print(error_message)
            self.show_error("Form Reset Error", error_message)


    def on_row_selected(self, current: QModelIndex, db_view: str, table_view: QTableView):
        """
        Handles the event when a row is selected in a table view.
        """
        if not current.isValid():
            return

        try:
            row_id = current.sibling(current.row(), 0).data()
            print(f"Selected ID from {db_view}: {row_id}")

            # Update corresponding detail table view
            if table_view.objectName() in self.detail_mapping:
                if table_view.objectName() == "tv_rechnungen":
                    self.load_invoice_positions(row_id)
                elif table_view.objectName() == "tv_dienstleister":
                    self.load_service_provider_details(row_id)

            # Update textboxes and lbl_eintrag_erstellt_datum
            self.update_form_and_label(current, table_view)
        except Exception as e:
            error_message = f"Error handling row selection in {db_view}: {e}\n{traceback.format_exc()}"
            print(error_message)
            self.show_error("Row Selection Error", error_message)

    def update_form_and_label(self, current: QModelIndex, table_view: QTableView):
        """
        Updates the right-side form and lbl_eintrag_erstellt_datum with the selected row's data.
        Dynamically identifies and updates QLineEdit, QComboBox, and QDoubleSpinBox widgets.
        """
        model = current.model()
        if not model:
            return

        try:
            for col in range(model.columnCount()):
                column_name = model.headerData(col, Qt.Orientation.Horizontal)
                value = current.sibling(current.row(), col).data()
                widget = self.findChild((QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit), f"{table_view.objectName()}_{column_name}")

                # Update QLineEdit (textbox)
                if isinstance(widget, QLineEdit):
                    widget.setText(str(value) if value is not None else "")
                    widget.setEnabled(False)

                # Update QComboBox
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(str(value) if value is not None else "")
                    widget.setEnabled(False)

                # Update QDoubleSpinBox
                elif isinstance(widget, QDoubleSpinBox):
                    try:
                        widget.setValue(float(value)) if value is not None else widget.setValue(0.0)
                    except (ValueError, TypeError):
                        widget.setValue(0.0)  # Set to default value if conversion fails
                    widget.setEnabled(False)

                elif isinstance(widget, QTextEdit):
                    widget.setText(value if value is not None else "")
                    widget.setEnabled(False)

            # Update the lbl_eintrag_erstellt_datum
            eintrag_datum = None
            for col in range(model.columnCount()):
                header = model.headerData(col, Qt.Orientation.Horizontal)
                if header == "CREATION_DATE":
                    eintrag_datum = current.sibling(current.row(), col).data()
                    break

            lbl_creation_date = self.findChild(QLabel, "lbl_eintrag_erstellt_datum")
            if lbl_creation_date:
                lbl_creation_date.setText(f"Erstellt am: {eintrag_datum}" if eintrag_datum else "Erstellt am: N/A")

                # List all referenced CEOs for the selected service provider
                if table_view.objectName() == "tv_dienstleister":
                    service_provider_id = current.sibling(current.row(),
                                                          0).data()  # Assuming the first column contains the ID
                    ceo_line_edit = self.findChild(QLineEdit, "tv_dienstleister_CEOS")
                    if ceo_line_edit:
                        ceo_names = self.get_ceos_for_service_provider(service_provider_id)
                        ceo_line_edit.setText(", ".join(ceo_names))
                        ceo_line_edit.setEnabled(False)
        except Exception as e:
            error_message = f"Error updating form and label: {e}\n{traceback.format_exc()}"
            print(error_message)
            self.show_error("Form Update Error", error_message)

    def get_ceos_for_service_provider(self, service_provider_id: str):
        """
        Retrieves the names of all CEOs associated with a given service provider.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT CEO_NAME
                    FROM REF_LABOR_COST AS rlc
                    JOIN CEO AS ceo ON rlc.FK_ST_NR = ceo.ST_NR
                    WHERE rlc.FK_UST_IDNR = ?
                """, (service_provider_id,))
                ceo_names = [row[0] for row in cursor.fetchall()]
            return ceo_names
        except sqlite3.OperationalError as e:
            error_message = f"Database error while retrieving CEOs for service provider ID {service_provider_id}: {e}"
            print(error_message)
            self.show_error("Database Error", error_message)
            return []
        except Exception as e:
            error_message = f"Unexpected error while retrieving CEOs for service provider ID {service_provider_id}: {e}\n{traceback.format_exc()}"
            print(error_message)
            self.show_error("Unexpected Error", error_message)
            return []

    def load_service_provider_details(self, service_provider_id: str):
        """
        Loads CEO and bank details for a selected service provider.
        """
        try:
            print(f"Loading service provider details for ID: {service_provider_id}")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT CEO_NAME, IBAN, BANK_NAME, BIC
                    FROM ceo_bank_view
                    WHERE UST_IDNR = ?
                """, (service_provider_id,))
                data = cursor.fetchall()

            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["CEO Name", "IBAN", "Kreditinstitut", "BIC"])
            for row in data:
                items = [QStandardItem(str(cell)) for cell in row]
                model.appendRow(items)

            self.tv_detail_dienstleister.setModel(model)
        except sqlite3.OperationalError as e:
            error_message = f"Database error while loading CEO and bank data: {e}"
            print(error_message)
            self.show_error("Database Error", error_message)
        except Exception as e:
            error_message = f"Unexpected error while loading CEO and bank data: {e}\n{traceback.format_exc()}"
            print(error_message)
            self.show_error("Unexpected Error", error_message)

    def load_invoice_positions(self, invoice_id: str):
        """
        Loads positions for a selected invoice.
        """
        try:
            print(f"Loading invoice positions for ID: {invoice_id}")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT p.POS_ID, p.NAME, p.DESCRIPTION, p.AREA, p.UNIT_PRICE
                    FROM POSITIONS AS p
                    JOIN INVOICES AS i ON p.FK_INVOICE_NR = i.INVOICE_NR
                    WHERE i.INVOICE_NR = ?
                """, (invoice_id,))
                data = cursor.fetchall()

            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["Position ID", "Name", "Description", "Area", "Unit Price"])
            for row in data:
                items = [QStandardItem(str(cell)) for cell in row]
                model.appendRow(items)

            self.tv_detail_rechnungen.setModel(model)
        except sqlite3.OperationalError as e:
            error_message = f"Database error while loading invoice positions: {e}"
            print(error_message)
            self.show_error("Database Error", error_message)
        except Exception as e:
            error_message = f"Unexpected error while loading invoice positions: {e}\n{traceback.format_exc()}"
            print(error_message)
            self.show_error("Unexpected Error", error_message)

    def show_error(self, title: str, message: str):
        """
        Displays an error message in a QMessageBox.
        """
        QMessageBox.critical(self, title, message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())