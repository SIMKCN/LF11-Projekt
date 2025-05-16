# This is the entry point of the application

import sys
from PyQt6.QtWidgets import QApplication
from mainwindow import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())