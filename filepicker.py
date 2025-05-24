from PyQt6 import uic
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QListWidget, QFileDialog
)

class FileUploader(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("Qt/file_uploader_list.ui", self)

        self.browseButton: QPushButton = self.findChild(QPushButton, "durchsuchen_button")
        self.uploadButton: QPushButton = self.findChild(QPushButton, "hochladen_button")
        self.fileListWidget: QListWidget = self.findChild(QListWidget, "datein_list_widget")

        self.selected_files = []

        self.browseButton.clicked.connect(self.browse_files)
        self.uploadButton.clicked.connect(self.upload_files)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Logo auswählen")
        if files:
            self.selected_files = files
            self.fileListWidget.clear()
            self.fileListWidget.addItems(files)

    def upload_files(self):
        if not self.selected_files:
            print("Kein Logo ausgewählt")
            return
        for file in self.selected_files:
            return file
            

if __name__ == "__main__":
    app = QApplication([])
    window = FileUploader()
    window.show()
    app.exec()
