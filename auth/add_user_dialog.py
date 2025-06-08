from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox

from auth.user_management import get_all_permissions, update_user, add_user


class AddUserDialog(QDialog):
    def __init__(self, parent=None, user=None):
        super().__init__(parent)
        uic.loadUi("Qt/add_user_dialog.ui", self)
        self.user = user  # None = neuer User, sonst dict mit id, username, permissions
        self._fill_permissions()
        if user:
            self.editUsername.setText(user["username"])
            self.editUsername.setDisabled(True)  # Username nicht editierbar
            self.setWindowTitle("Nutzer bearbeiten")
            self._select_user_permissions(user["permissions"])
        else:
            self.setWindowTitle("Neuen Nutzer anlegen")
        self.btnSave.clicked.connect(self.save)
        self.btnCancel.clicked.connect(self.reject)

    def _fill_permissions(self):
        self.listPermissions.clear()
        for pid, pname in get_all_permissions():
            self.listPermissions.addItem(pname)
            self.listPermissions.item(self.listPermissions.count() - 1).setData(0x0100, pid)

    def _select_user_permissions(self, permissions):
        for idx in range(self.listPermissions.count()):
            item = self.listPermissions.item(idx)
            if item.text() in permissions:
                item.setSelected(True)

    def save(self):
        username = self.editUsername.text().strip()
        pw1 = self.editPassword1.text()
        pw2 = self.editPassword2.text()
        perms = [self.listPermissions.item(i).data(0x0100)
                 for i in range(self.listPermissions.count())
                 if self.listPermissions.item(i).isSelected()]
        if not username:
            QMessageBox.warning(self, "Fehler", "Benutzername darf nicht leer sein.")
            return
        if self.user is None:  # Neuer User
            if not pw1 or not pw2:
                QMessageBox.warning(self, "Fehler", "Passwort eingeben.")
                return
            if pw1 != pw2:
                QMessageBox.warning(self, "Fehler", "Passwörter stimmen nicht überein.")
                return
            try:
                add_user(username, pw1, perms)
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Fehler beim Anlegen: {e}")
                return
        else:
            password = pw1 if pw1 == pw2 and pw1 else None
            if (pw1 or pw2) and pw1 != pw2:
                QMessageBox.warning(self, "Fehler", "Passwörter stimmen nicht überein.")
                return
            try:
                update_user(self.user["id"], username, password, perms)
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Fehler beim Bearbeiten: {e}")
                return
        self.accept()