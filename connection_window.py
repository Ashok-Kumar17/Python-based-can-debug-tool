from PySide6.QtWidgets import (
    QMainWindow,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QWidget,
    )
from PySide6.QtCore import Qt

class ConnectionWindow(QMainWindow):
    def __init__(self, parent=None):
        """Initializer for the Connection Window."""
        super().__init__(parent)
        self.setWindowTitle("Connection Window")
        self.resize(400, 300)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        label = QLabel("This is the Connection Window.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        