 """
TODO: Abhängigkeiten einfügen
 """
 
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