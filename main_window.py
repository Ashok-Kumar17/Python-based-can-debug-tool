from PySide6.QtWidgets import QMainWindow, QApplication
from can_message_ui import CANMessageUI
from connection_window import ConnectionWindow
from PySide6.QtGui import QAction

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        """Initializer."""
        super().__init__(parent)
        self.setWindowTitle("Infinity beta V0.2.0")
        self.resize(1000, 800)

        self.widget_window = CANMessageUI()
        self.setCentralWidget(self.widget_window)

        self.create_menu_bar()
        self.connection_window = None

    def create_menu_bar(self):
        """
        Create a menu bar with a single menu and action.
        """
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("Connection")

        example_action = QAction("Open Connection Window", self)
        example_action.triggered.connect(self.example_action_triggered)
        file_menu.addAction(example_action)

    def example_action_triggered(self):
        """
        Handle the Example Action click event.
        Open the Connection Window.
        """
        if not self.connection_window:
            self.connection_window = ConnectionWindow(self)
        self.connection_window.show()

    def closeEvent(self, event):
        """
        Handle the window close event to clean up resources.
        """
        if self.widget_window.on_exit() == True:
            event.accept()
        else:
            event.ignore()
