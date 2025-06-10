from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QMessageBox, QTableWidgetItem, QPushButton, QTableWidget, QHeaderView

from auth.add_user_dialog import AddUserDialog
from auth.user_management import get_users_with_permissions, delete_user


class UserManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("Qt/user_management_dialog.ui", self)
        self.resize(600, 400)

        # Connect Signal for Click on 'btnAddUser'
        self.btnAddUser = self.findChild(QPushButton, "btnAddUser")
        if self.btnAddUser:
            self.btnAddUser.clicked.connect(self.add_user)
        # Connect Signal for Click on 'btnEditUser'
        self.btnEditUser = self.findChild(QPushButton, "btnEditUser")
        if self.btnEditUser:
            self.btnEditUser.clicked.connect(self.edit_user)
        # Connect Signal for Click on 'btnDeleteUser'
        self.btnDeleteUser = self.findChild(QPushButton, "btnDeleteUser")
        if self.btnDeleteUser:
            self.btnDeleteUser.clicked.connect(self.delete_user)

        self.tableUsers = self.findChild(QTableWidget, "tableUsers")
        if self.tableUsers:
            header = self.tableUsers.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.tableUsers.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            self.tableUsers.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self.load_users()

    def load_users(self):
        self.tableUsers.setRowCount(0)
        users = get_users_with_permissions()
        for row, user in enumerate(users):
            # robustes Unpacking
            uid = user[0] if len(user) > 0 else ""
            username = user[1] if len(user) > 1 else ""
            perms = user[2] if len(user) > 2 else ""
            self.tableUsers.insertRow(row)
            self.tableUsers.setItem(row, 0, self._make_item(str(uid)))
            self.tableUsers.setItem(row, 1, self._make_item(username))
            self.tableUsers.setItem(row, 2, self._make_item(perms or ""))

    def _make_item(self, text):
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
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
        dialog = AddUserDialog(self)
        dialog.user_changed.connect(self.load_users)
        dialog.exec()

    def edit_user(self):
        user = self.get_selected_user()
        if not user:
            QMessageBox.warning(self, "Fehler", "Bitte einen Nutzer auswählen.")
            return
        dialog = AddUserDialog(self, user=user)
        dialog.user_changed.connect(self.load_users)
        dialog.exec()

    def delete_user(self):
        user = self.get_selected_user()
        if not user:
            QMessageBox.warning(self, "Fehler", "Bitte einen Nutzer auswählen.")
            return
        res = QMessageBox.question(
            self,
            "Nutzer löschen",
            f"Nutzer '{user['username']}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            delete_user(user["id"])
            self.load_users()