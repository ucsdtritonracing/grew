from PySide6 import QApplication, QMainWindow, QPushButton, QWidget, QVBoxLayout, QLabel
class MainWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main Window")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()
        label = QLabel("This is the main window.")
        button = QPushButton("Open Second Widget")
        button.clicked.connect(self.openPDU) # Connect button click to a method
    def openPDU(self):
        print("yeehaw")