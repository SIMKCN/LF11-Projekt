from PyQt6.QtWidgets import QDialog, QLineEdit, QLabel, QPushButton, QVBoxLayout, QMessageBox

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Anmeldung")

        self.label_user = QLabel("Benutzername:")
        self.edit_user = QLineEdit()
        self.label_pass = QLabel("Passwort:")
        self.edit_pass = QLineEdit()
        self.edit_pass.setEchoMode(QLineEdit.EchoMode.Password)

        self.btn_login = QPushButton("Anmelden")
        self.btn_login.clicked.connect(self.try_login)

        layout = QVBoxLayout()
        layout.addWidget(self.label_user)
        layout.addWidget(self.edit_user)
        layout.addWidget(self.label_pass)
        layout.addWidget(self.edit_pass)
        layout.addWidget(self.btn_login)
        self.setLayout(layout)

        self.success = False
        self._login_in_progress = False  # Verhindert mehrfaches Auslösen
        self._user_id = None

    def try_login(self):
        if self._login_in_progress:
            return
        self._login_in_progress = True

        username = self.edit_user.text().strip()
        password = self.edit_pass.text()
        from auth.user_management import check_user_credentials, get_user_id_by_username
        if check_user_credentials(username, password):
            self.success = True
            self._user_id = get_user_id_by_username(username)  # Hole user_id aus der DB
            self.accept()
        else:
            QMessageBox.warning(self, "Anmeldungsfehler", "Die eingegebenen Nutzerdaten wurden nicht gefunden\n"
                                                          "Bitte prüfen Sie Ihre Eingabe.")
            self.edit_pass.clear()
            self.edit_pass.setFocus()
        self._login_in_progress = False

    def get_user_id(self):
        return self._user_id