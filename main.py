import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from PyQt6.QtWidgets import QApplication, QMessageBox
from config import IS_AUTHENTICATION_ACTIVE
from mainwindow import MainWindow

def main():
    app = QApplication(sys.argv)

    user_id = None
    username = None

    if IS_AUTHENTICATION_ACTIVE:
        from auth.login_dialog import LoginDialog
        login = LoginDialog()
        if login.exec() != login.DialogCode.Accepted or not getattr(login, "success", True):
            sys.exit(0)
        # Hole user_id und username nach erfolgreichem Login
        user_id = login.get_user_id()
        username = login.edit_user.text().strip()
        if not user_id:
            QMessageBox.critical(None, "Anmeldefehler", "Ihre eingegebenen Benutzerdaten wurden nicht gefunden!\n"
                                                        "Haben Sie sich eingeloggt?")
            sys.exit(1)
    else:
        user_id = None  # z.B. 0 für Gast
        username = "Gast"

    window = MainWindow(user_id=user_id, username=username)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()