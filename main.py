import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from config import IS_AUTHENTICATION_ACTIVE
from mainwindow import MainWindow

def main():
    app = QApplication(sys.argv)

    username = None  # Standardwert

    if IS_AUTHENTICATION_ACTIVE:
        from auth.login_dialog import LoginDialog
        login = LoginDialog()
        if login.exec() != login.DialogCode.Accepted or not getattr(login, "success", True):
            sys.exit(0)
        username = login.edit_user.text().strip()
    else:
        username = "Gast"  # Oder lasse username=None

    window = MainWindow(username=username)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()