 """
TODO: Abhängigkeiten einfügen
 """


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