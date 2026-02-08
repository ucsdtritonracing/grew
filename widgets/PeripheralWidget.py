from PySide6 import QtWidgets, QtCore

class PeripheralWidget(QtWidgets.QWidget, QtCore.QObject):
    def __init__(self, peripheral):
        super().__init__()
        self.peripheral = peripheral
    def getPeripheral(self):
        return self.peripheral