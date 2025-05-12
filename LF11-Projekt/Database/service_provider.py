 """
TODO: Abhängigkeiten einfügen
 """

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