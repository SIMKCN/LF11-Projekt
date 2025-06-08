from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QMessageBox

from auth.add_user_dialog import AddEditUserDialog
from auth.user_management import get_users_with_permissions, delete_user


class UserManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("Qt/user_management_dialog.ui", self)
        self.load_users()
        self.btnAddUser.clicked.connect(self.add_user)
        self.btnEditUser.clicked.connect(self.edit_user)
        self.btnDeleteUser.clicked.connect(self.delete_user)

    def load_users(self):
        self.tableUsers.setRowCount(0)
        users = get_users_with_permissions()
        for row, (uid, username, perms) in enumerate(users):
            self.tableUsers.insertRow(row)
            self.tableUsers.setItem(row, 0, self._make_item(str(uid)))
            self.tableUsers.setItem(row, 1, self._make_item(username))
            self.tableUsers.setItem(row, 2, self._make_item(perms or ""))

    def _make_item(self, text):
        from PyQt5.QtWidgets import QTableWidgetItem
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~0x2)  # Nicht editierbar
        return item

    def get_selected_user(self):
        row = self.tableUsers.currentRow()
        if row < 0:
            return None
        uid = int(self.tableUsers.item(row, 0).text())
        username = self.tableUsers.item(row, 1).text()
        perms = [p.strip() for p in (self.tableUsers.item(row, 2).text() or "").split(",") if p.strip()]
        return {"id": uid, "username": username, "permissions": perms}

    def add_user(self):
        dialog = AddEditUserDialog(self)
        if dialog.exec_() == dialog.Accepted:
            self.load_users()

    def edit_user(self):
        user = self.get_selected_user()
        if not user:
            QMessageBox.warning(self, "Fehler", "Bitte einen Nutzer auswählen.")
            return
        dialog = AddEditUserDialog(self, user=user)
        if dialog.exec_() == dialog.Accepted:
            self.load_users()

    def delete_user(self):
        user = self.get_selected_user()
        if not user:
            QMessageBox.warning(self, "Fehler", "Bitte einen Nutzer auswählen.")
            return
        res = QMessageBox.question(self, "Nutzer löschen", f"Nutzer '{user['username']}' wirklich löschen?")
        if res == QMessageBox.Yes:
            delete_user(user["id"])
            self.load_users()