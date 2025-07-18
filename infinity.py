from PySide6.QtWidgets import QApplication
from main_window import MainWindow

if __name__ == "__main__":
    app = QApplication([])
    with open("styles.qss", "r") as file:
        print("[DEBUG] Loading QSS file")
        app.setStyleSheet(file.read())

    window = MainWindow()
    window.show()
    app.exec()