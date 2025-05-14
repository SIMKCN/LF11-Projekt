   """
TODO: Abhängigkeiten einfügen
 """
  
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
